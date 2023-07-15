import asyncio
import sys
import traceback
import json
from enum import Enum, auto
from typing import Literal, List, Optional, NamedTuple
from argparse import Namespace

from .base_kernel import BaseKernel

"""
Auto-compile C/C++ cells into object files.
The compiler for a kernel is specified at install-time.
Code cells are saved to a temporary file and compiled into .o files
.o files are scanned for main()

A cell containing main() must specify which other cells (if any) it uses so
that linking can take place.

To auto-compile, need to be able to specify:
    - compilation flags e.g. CFLAGS
    - linker flags (not used unless the cell is linked to an executable)
    - compiler options e.g. -g

Args for auto-compilation are given in comments, with sensible defaults.
-Wall -Wextra are on by default
Default to -std=c11 and -std=c++17

Arguments *required* by the user:
    - a name for the source file (.c/.cpp/.h)

Cells named *.h are just saved and are not auto-compiled
Cells named *.c/*.cpp are saved to a temporary file and auto-compiled into *.o

Where to store the .o file?
    - in user-specified location
    - in memory as some bytes array, used on-command?
```
"""

class Lang(Enum):
    C = auto()
    CPP = auto()
    
language = {
    "c": Lang.C,
    "cpp": Lang.CPP,
    "cxx": Lang.CPP,
    "cc": Lang.CPP,
}

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
        "LDFLAGS"
    ]

    async def do_execute(self, *args, **kwargs):
        """Catch all exceptions and report them in the notebook"""
        result = None
        try:
            result = await self.do_execute_with_try_except(*args, **kwargs)
        except Exception:
            message, result = self.error_from_exception(*sys.exc_info())
            self.send_text("stderr", message)
        finally:
            return result

    async def do_execute_with_try_except(self, code: str, silent, store_history=True, user_expressions=None, allow_stdin=False, cell_id=None):
        """
        Algorithm:
            - scan for magics (?)
                - if the cell contains 1 line and is a line magic, process it using super().do_execute
                - if cell magic present, process it using super().do_execute and don't process cell as code
            - if cell is not named, report an error e.g. //// src/shapes.cpp
            - scan for comment-options
                - //%CC (to choose a compiler different from the one attached to this kernel)
                - //%CFLAGS
                - //%LDFLAGS

        Questions:
            - how does the IPython shell intercept & interpret magic commands?
        """

        # Scan for magics
        if (len(code.splitlines()) == 1 and code.startswith("%")
            or code.startswith("%%")
        ):
            return await super().do_execute(code, silent, store_history=store_history, user_expressions=user_expressions, allow_stdin=allow_stdin, cell_id=cell_id)
        
        # Cell must be named
        if not code.startswith(self._tag_name):
            message = f"code cell must start with \"{self._tag_name} [filename]\""
            self.send_text("stderr", message + "\n")
            return error("NotNamed", message)
        else:
            name = code[len(self._tag_name):code.find("\n")].strip()
            with open(name, "w") as src:
                src.write(code)
        
        args = self.parse_args(code)
        compile = self.get_compiler_command(args)
        # self.send_text("stderr", json.dumps(args.__dict__, indent=2) + "\n")
        self.send_text("stdout", f"$> {compile}\n")
        await self.exec_command(compile)
        await self.exec_command(self.get_command_detect_main(args))
        return ok(self.execution_count)

    def parse_args(self, code: str) -> Namespace:
        args = self.default_compiler_args()
        header, *lines = code.splitlines()
        assert header.startswith(self._tag_name)
        args.name = header.removeprefix(self._tag_name).strip()

        # Detect language used
        name, ext = args.name.split(".")
        args.language = language[ext]
        args.obj = name + ".o"

        # Detect options
        for k, line in enumerate(lines, start=2):
            if line.startswith(self._tag_opt) and len(line.rstrip()) > len(self._tag_opt):
                opt, _, rest = line.removeprefix(self._tag_opt).strip().partition(" ")
                if opt not in self._known_opts:
                    self.send_text("stderr", f"unknown option on line {k}: {opt}\n")
                else:
                    setattr(args, opt, rest)

        # Set the compiler
        if args.language == Lang.C:
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

        return args
    
    def get_compiler_command(self, args) -> str:
        return f"""{args.compiler} {args.cflags} {args.LDFLAGS} -c {args.name} -o {args.obj}"""
    
    def get_command_detect_main(self, args) -> str:
        return f"""nm {args.obj}"""
    
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

    async def exec_command(self, command: str, silent: bool = False):
        proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        if silent:
            streams = ()
        else:
            streams = self.stream_data(proc.stdout, "stdout"), self.stream_data(proc.stderr, "stderr")
        await asyncio.gather(*streams, proc.wait())
        if proc.returncode != 0:
            self.send_text("stderr", f"command failed with exit code {proc.returncode}: {command}")

    async def stream_data(self, stream: asyncio.StreamReader, name: Literal["stderr", "stdout"]) -> None:
        async for data in stream:
            self.send_text(name, data.decode())
