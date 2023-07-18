from __future__ import annotations
import asyncio
import sys
import traceback
import json
from enum import Enum, auto
from typing import Literal, List, Optional, Callable, Coroutine
from argparse import Namespace

from .base_kernel import BaseKernel, Stream, STDERR, STDOUT

StreamConsumer = Callable[[asyncio.StreamReader], Coroutine[None, None, None]]

class Lang(Enum):
    C = auto()
    CPP = auto()
    
language = {
    "c": Lang.C,
    "cpp": Lang.CPP,
    "cxx": Lang.CPP,
    "cc": Lang.CPP,
}


class AsyncCommand:

    def __init__(self, command: str) -> None:
        self._command: str = command

    @property
    def string(self) -> str:
        return self._command

    async def run(self: AsyncCommand, stdout: Optional[StreamConsumer] = None, stderr: Optional[StreamConsumer] = None) -> int:
        proc = await asyncio.create_subprocess_shell(self._command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        streams = []
        if stdout is not None:
            streams.append(stdout(proc.stdout))
        if stderr is not None:
            streams.append(stderr(proc.stderr))
        await asyncio.gather(*streams, proc.wait())
        return proc.returncode

def error(ename: str, evalue: str, tb: Optional[list[str]] = None) -> dict[str, str | list[str]]:
    return {
        "status": "error",
        "ename": ename,
        "evalue": evalue,
        "traceback": tb or []
    }

def ok(execution_count: int) -> dict[str, str | int]:
    return {
        "status": "ok",
        "execution_count": execution_count
    }


class AutoCompileKernel(BaseKernel):
    """Auto compile C/C++ cells"""

    _tag_name = "////"
    _tag_opt =  "//%"
    _known_opts = [
        "CC",
        "CXX",
        "CFLAGS",
        "CXXFLAGS",
        "LDFLAGS",
        "DEPENDS"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def do_execute(self, *args, **kwargs):
        """Catch all exceptions and report them in the notebook"""
        result = None
        try:
            result = await self.autocompile(*args, **kwargs)
        except Exception:
            message, result = self.error_from_exception(*sys.exc_info())
            self.print(message, dest=STDERR)
        finally:
            return result

    async def autocompile(self, code: str, silent, store_history=True, user_expressions=None, allow_stdin=False, cell_id=None):

        # Scan for magics
        if (len(code.splitlines()) == 1 and code.startswith("%")
            or code.startswith("%%")
        ):
            return await super().do_execute(code, silent, store_history=store_history, user_expressions=user_expressions, allow_stdin=allow_stdin, cell_id=cell_id)
        
        # Cell must be named
        if not code.startswith(self._tag_name):
            message = f"code cell must start with \"{self._tag_name} [filename]\""
            self.print(message, dest=STDERR)
            return error("NotNamed", message)
        else:
            name = code[len(self._tag_name):code.find("\n")].strip()
            with open(name, "w") as src:
                src.write(code)
                self.print(f"wrote file {name}")
        
        # Get args specified in the code cell
        args = self.parse_args(code)

        if False:
            # TODO: add option for user to enable this
            self.print(json.dumps(args.__dict__, indent=2), STDERR)

        if args.compiler is None:
            # No compiler means nothing to compile, so exit
            return ok(self.execution_count)

        # Attempt to compile to .o
        compile = self.command_compile(args.compiler, args.cflags, args.LDFLAGS, args.name, args.obj)
        self.print(f"$> {compile.string}")
        result = await compile.run(self.stream_stdout, self.stream_stderr)
        if result != 0:
            self.print(f"compilation failed with exit code {result}", dest=STDERR)

        # Detect whether the cell defines a main function
        if await self.command_detect_main(args.obj).run() != 0:
            # No main defined, so we're finished
            return ok(self.execution_count)

        # Since main was defined, attempt to link an executable
        link_exe = self.command_link_exe(args.compiler, args.LDFLAGS, args.exe, args.obj, args.depends)
        self.print(f"$> {link_exe.string}")
        result = await link_exe.run(self.stream_stdout, self.stream_stderr)
        if result != 0:
            self.print(f"linking failed with exit code {result}", dest=STDERR)

        # Attempt to run the executable
        run_exe = self.command_exec(f"./{args.exe}")
        self.print(f"$> {run_exe.string}")
        result = await run_exe.run(self.stream_stdout, self.stream_stderr)
        if result != 0:
            self.print(f"executable failed with exit code {result}", dest=STDERR)

        return ok(self.execution_count)

    def parse_args(self, code: str) -> Namespace:
        args = self.default_compiler_args()
        header, *lines = code.splitlines()
        assert header.startswith(self._tag_name)
        args.name = header.removeprefix(self._tag_name).strip()

        # Detect language used
        basename, ext = args.name.split(".")
        args.language = language.get(ext)
        args.obj = basename + ".o"
        args.exe = basename

        # Detect options
        for k, line in enumerate(lines, start=2):
            if line.startswith(self._tag_opt) and len(line.rstrip()) > len(self._tag_opt):
                opt, _, rest = line.removeprefix(self._tag_opt).strip().partition(" ")
                if opt not in self._known_opts:
                    self.print(f"unknown option on line {k}: {opt}", STDERR)
                else:
                    setattr(args, opt, rest)

        # Set the compiler
        if args.language is None:
            args.compiler = None
        elif args.language == Lang.C:
            args.compiler = args.CC or self.ckargs.CC
        elif args.language == Lang.CPP:
            args.compiler = args.CXX or self.ckargs.CXX
        else:
            raise ValueError(f"don't know which compiler for extension {ext}")
        
        # Set the compilation flags:
        if args.language == Lang.C:
            args.cflags = args.CFLAGS
        else:
            args.cflags = args.CXXFLAGS

        # Set the .o dependencies:
        args.depends = args.DEPENDS

        return args
    
    def command_compile(self: AutoCompileKernel, compiler: str, cflags: str, ldflags: str, name: str, objfile: str) -> AsyncCommand:
        return AsyncCommand(f"""{compiler} {cflags} {ldflags} -c {name} -o {objfile}""")
    
    def command_detect_main(self, objfile: str) -> AsyncCommand:
        return AsyncCommand(f"""nm {objfile} | grep " T main" """)
    
    def command_link_exe(self, compiler: str, ldflags: str, exe: str, objname: str, depends: str) -> AsyncCommand:
        return AsyncCommand(f"{compiler} {ldflags} {depends} {objname} -o {exe}")

    def command_exec(self, exe: str) -> AsyncCommand:
        return AsyncCommand(exe)
    
    @classmethod
    def default_compiler_args(cls, extra: Optional[List[str]] = None) -> Namespace:
        "Return a namespace with known (and any extra) options set to \"\""
        extra = extra or []
        args = Namespace(**{opt: "" for opt in (cls._known_opts + extra)})
        return args
    
    @staticmethod
    def error_from_exception(exc_type, exc, tb):
        tb_str = "\n".join(traceback.format_tb(tb))
        message = f"{tb_str}\n{exc_type.__name__}: {exc}"
        return message, error(exc_type.__name__, str(exc), traceback.format_tb(tb))

    async def stream_data(self, dest: Stream, reader: asyncio.StreamReader, end: str = "") -> None:
        async for data in reader:
            self.print(data.decode(), dest=dest, end=end)

    def stream_stdout(self, reader: asyncio.StreamReader) -> Coroutine[None, None, None]:
        return self.stream_data(STDOUT, reader, end="")

    def stream_stderr(self, reader: asyncio.StreamReader) -> Coroutine[None, None, None]:
        return self.stream_data(STDERR, reader, end="")
