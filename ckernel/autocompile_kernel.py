"""Implements AutoCompileKernel"""

from __future__ import annotations
import sys
import os
import json
from typing import List, Optional
from argparse import Namespace

from .base_kernel import BaseKernel, STDERR
from .util import AsyncCommand, Lang, language, success, error, error_from_exception


class AutoCompileKernel(BaseKernel):
    """Auto compile C/C++ cells"""

    _tag_name = "////"
    _tag_opt = "//%"
    _known_opts = ["CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "DEPENDS", "VERBOSE"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CC = os.getenv("CKERNEL_CC")
        self.CXX = os.getenv("CKERNEL_CXX")

    async def do_execute(self, *args, **kwargs):
        """Catch all exceptions and report them in the notebook"""
        result = None
        try:
            result = await self.autocompile(*args, **kwargs)
        except Exception:  # pylint: disable=broad-exception-caught
            message, result = error_from_exception(*sys.exc_info())
            self.print(message, dest=STDERR)
        return result

    async def autocompile(
        self,
        code: str,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
        cell_id=None,
    ):
        """Auto-compile (and possibly execute) a code cell"""

        # Scan for magics
        if (
            len(code.splitlines()) == 1
            and code.startswith("%")
            or code.startswith("%%")
        ):
            return await super().do_execute(
                code,
                silent,
                store_history=store_history,
                user_expressions=user_expressions,
                allow_stdin=allow_stdin,
                cell_id=cell_id,
            )

        # Cell must be named
        if not code.startswith(self._tag_name):
            message = f'[ERROR] code cell must start with "{self._tag_name} [filename]"'
            self.print(message, dest=STDERR)
            return error("NotNamed", message)

        # Get args specified in the code cell
        args = self.parse_args(code)

        if args.verbose:
            nonempty_args = {k: v for k, v in args.__dict__.items() if v != ""}
            self.print(json.dumps(nonempty_args, indent=2), STDERR)

        with open(args.filename, "w", encoding="utf-8") as src:
            src.write(code)
            self.print(f"wrote file {args.filename}")

        if args.compiler is None:
            # No compiler means nothing to compile, so exit
            return success(self.execution_count)

        # Attempt to compile to .o
        compile_cmd = self.command_compile(
            args.compiler, args.cflags, args.LDFLAGS, args.filename, args.obj
        )
        self.print(f"$> {compile_cmd.string}")
        result = await compile_cmd.run(self.stream_stdout, self.stream_stderr)
        if result != 0:
            self.print(f"compilation failed with exit code {result}", dest=STDERR)

        # Detect whether the cell defines a main function
        if await self.command_detect_main(args.obj).run() != 0:
            # No main defined, so we're finished
            return success(self.execution_count)

        # Since main was defined, attempt to link an executable
        link_exe = self.command_link_exe(
            args.compiler, args.LDFLAGS, args.exe, args.obj, args.depends
        )
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

        return success(self.execution_count)

    def parse_args(self, code: str) -> Namespace:
        args = self.default_compiler_args()
        header, *lines = code.splitlines()
        assert header.startswith(self._tag_name)
        args.filename = header.removeprefix(self._tag_name).strip()

        # Detect language used
        basename, ext = args.filename.split(".")
        args.language = language.get(ext)
        args.obj = basename + ".o"
        args.exe = basename

        # Detect options
        for k, line in enumerate(lines, start=2):
            if line.startswith(self._tag_opt) and len(line.rstrip()) > len(
                self._tag_opt
            ):
                opt, _, rest = line.removeprefix(self._tag_opt).strip().partition(" ")
                if opt not in self._known_opts:
                    self.print(f"unknown option on line {k}: {opt}", STDERR)
                elif opt == "VERBOSE":
                    args.verbose = True
                else:
                    setattr(args, opt, rest)

        # Set the compiler
        if args.language is None:
            args.compiler = None
        elif args.language == Lang.C:
            args.compiler = args.CC or self.CC
        elif args.language == Lang.CPP:
            args.compiler = args.CXX or self.CXX
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

    def command_compile(
        self: AutoCompileKernel,
        compiler: str,
        cflags: str,
        ldflags: str,
        name: str,
        objfile: str,
    ) -> AsyncCommand:
        return AsyncCommand(f"""{compiler} {cflags} {ldflags} -c {name} -o {objfile}""")

    def command_detect_main(self, objfile: str) -> AsyncCommand:
        return AsyncCommand(f"""nm {objfile} | grep " T main" """)

    def command_link_exe(
        self, compiler: str, ldflags: str, exe: str, objname: str, depends: str
    ) -> AsyncCommand:
        return AsyncCommand(f"{compiler} {ldflags} {depends} {objname} -o {exe}")

    def command_exec(self, exe: str) -> AsyncCommand:
        return AsyncCommand(exe)

    @classmethod
    def default_compiler_args(cls, extra: Optional[List[str]] = None) -> Namespace:
        "Return a namespace with known (and any extra) options set to an empty string"
        extra = extra or []
        args = Namespace(**{opt: "" for opt in (cls._known_opts + extra)})
        args.verbose = False
        return args
