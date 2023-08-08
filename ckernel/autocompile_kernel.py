"""Implements AutoCompileKernel"""

from __future__ import annotations
import json
import os
import sys
from contextlib import contextmanager
from argparse import Namespace
from typing import List, Optional

from .base_kernel import BaseKernel
from .util import (
    AsyncCommand,
    Lang,
    STDERR,
    error,
    error_from_exception,
    language,
    success,
)


class AutoCompileKernel(BaseKernel):
    """Auto compile C/C++ cells"""

    _tag_name = "////"
    _tag_opt = "//%"
    _known_opts = [
        "CC",
        "CXX",
        "CFLAGS",
        "CXXFLAGS",
        "LDFLAGS",
        "DEPENDS",
        "VERBOSE",
        "ARGS",
        "NOCOMPILE",
        "NOEXEC",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CC = os.getenv("CKERNEL_CC")
        self.CXX = os.getenv("CKERNEL_CXX")
        self._active_commands: set[AsyncCommand] = set()

    async def do_execute(self, *args, **kwargs):
        """Catch all exceptions and report them in the notebook"""
        result = None
        try:
            result = await self.autocompile(*args, **kwargs)
        except Exception:  # pylint: disable=broad-exception-caught
            message, result = error_from_exception(*sys.exc_info())
            self.print(message, dest=STDERR)
        return result

    def do_shutdown(self, restart):
        """Process a restart/shutdown request"""
        for command in self._active_commands:
            self.log.error("kill %s", command)
            command.terminate()
        return super().do_shutdown(restart)

    @contextmanager
    def active_command(self, command: AsyncCommand):
        """Add a command to the set of active commands while it is active"""
        self._active_commands.add(command)
        yield
        try:
            self._active_commands.remove(command)
        except KeyError:
            self.log.error("active command not found: %s", command)

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
            self.debug_msg("executing magic command")
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

        if args.verbose or self.debug:
            nonempty_args = {k: v for k, v in args.__dict__.items() if v != ""}
            self.print(json.dumps(nonempty_args, indent=2), STDERR)

        with open(args.filename, "w", encoding="utf-8") as src:
            src.write(code)
            self.print(f"wrote file {args.filename}")

        if args.compiler is None or not args.should_compile:
            # No compiler means nothing to compile, so exit
            return success(self.execution_count)

        # Attempt to compile to .o silently. If successful, detect whether main was defined.
        compile_cmd = self.command_compile(
            args.compiler, args.cflags, args.LDFLAGS, args.filename, args.obj
        )
        self.debug_msg("attempt to compile to .o")
        result = await compile_cmd.run()  # silent
        if result != 0:
            # failed to compile to .o, so repeat loud to report error
            await compile_cmd.run(self.stream_stdout, self.stream_stderr)
            return error("CompileFailed", "Compilation failed")

        # compiled ok, continue to detect main
        self.debug_msg("detect whether main defined")
        if await self.command_detect_main(args.obj).run() != 0:
            # main not defined, so repeat to report compilation to .o and stop
            self.debug_msg("main not defined: compile to .o and stop")
            self.print(f"$> {compile_cmd.string}")
            await compile_cmd.run(self.stream_stdout, self.stream_stderr)
            return success(self.execution_count)
        else:
            # main was defined, so compile & link in one command & report, then attempt to execute
            self.debug_msg("main was defined: attempt to compile and run executable")
            compile_exe_cmd = self.command_compile_exe(
                args.compiler,
                args.cflags,
                args.LDFLAGS,
                args.filename,
                args.depends,
                args.exe,
            )
            self.print(f"$> {compile_exe_cmd.string}")
            result = await compile_exe_cmd.run(self.stream_stdout, self.stream_stderr)
            if result != 0:
                return error("CompileFailed", "Compilation failed")
            if not args.should_exec:
                return success(self.execution_count)
            run_exe = AsyncCommand(f"./{args.exe} {args.ARGS}", logger=self.log)
            self.print(f"$> {run_exe.string}")
            with self.active_command(run_exe):
                result = await run_exe.run(self.stream_stdout, self.stream_stderr)
            if result != 0:
                self.print(f"executable failed with exit code {result}", dest=STDERR)
                return error("ExeFailed", "Executable failed")
            return success(self.execution_count)

    def parse_args(self, code: str) -> Namespace:
        args = self.default_compiler_args()
        header, *lines = code.splitlines()
        self.debug_msg(f"{header=}")
        assert header.startswith(self._tag_name)
        args.filename = header.removeprefix(self._tag_name).strip()
        self.debug_msg(f"{args.filename=}")

        # Detect language used
        basename, ext = args.filename.split(".")
        self.debug_msg(f"{basename=}, {ext=}")
        args.language = language.get(ext)
        args.obj = basename + ".o"
        args.exe = basename

        args.should_compile = True
        args.should_exec = True

        # Detect options
        for k, line in enumerate(lines, start=2):
            if line.startswith(self._tag_opt) and len(line.rstrip()) > len(
                self._tag_opt
            ):
                opt, _, rest = line.removeprefix(self._tag_opt).strip().partition(" ")
                self.debug_msg(f"{opt=}, {rest=}")
                if opt not in self._known_opts:
                    self.print(f"unknown option on line {k}: {opt}", STDERR)
                elif opt == "VERBOSE":
                    args.verbose = True
                elif opt == "NOEXEC":
                    args.should_exec = False
                elif opt == "NOCOMPILE":
                    args.should_compile = False
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

    def command_compile_exe(
        self: AutoCompileKernel,
        compiler: str,
        cflags: str,
        ldflags: str,
        name: str,
        depends: str,
        exe: str,
    ) -> AsyncCommand:
        return AsyncCommand(f"{compiler} {cflags} {ldflags} {depends} {name} -o {exe}")

    def command_detect_main(self, objfile: str) -> AsyncCommand:
        return AsyncCommand(f"""nm {objfile} | grep " T main" """)

    def command_link_exe(
        self, compiler: str, ldflags: str, exe: str, objname: str, depends: str
    ) -> AsyncCommand:
        return AsyncCommand(f"{compiler} {ldflags} {depends} {objname} -o {exe}")

    @classmethod
    def default_compiler_args(cls, extra: Optional[List[str]] = None) -> Namespace:
        "Return a namespace with known (and any extra) options set to an empty string"
        extra = extra or []
        args = Namespace(**{opt: "" for opt in (cls._known_opts + extra)})
        args.verbose = False
        return args
