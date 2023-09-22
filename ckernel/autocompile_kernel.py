"""Implements AutoCompileKernel"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from argparse import Namespace
from contextlib import contextmanager
from typing import List, Optional

from . import resource
from .async_command import AsyncCommand
from .trigger import SysVSemTrigger
from .base_kernel import BaseKernel
from .util import (
    STDERR,
    Lang,
    error,
    error_from_exception,
    get_environment_variables,
    language,
    success,
    switch_directory,
    temporary_directory,
    is_macOS,
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
        self.env = get_environment_variables(default="")
        super().__init__(*args, **kwargs)

        # request a temporary working dir for this session
        self.twd = temporary_directory(prefix="ipython-ckernel-")
        self.log_info("cwd: %s", self.cwd)
        self.log_info("twd: %s", self.twd)

        # store active command(s) for safe termination
        self._active_commands: set[AsyncCommand] = set()

        # create a trigger for stdin
        self.stdin_trigger = SysVSemTrigger(logger=self.log)
        self.log_info("using trigger %s", self.stdin_trigger)

        # compile input wrappers
        dirname, ck_dyn_src = os.path.split(resource.input_wrappers_src)
        self.ck_dyn_obj = self.twd / "ckernel-input-wrappers.o"
        debug_flag = "-DCKERNEL_WITH_DEBUG" if self.debug else ""
        compile_cmd = AsyncCommand(
            f"{self.env.CKERNEL_CC} {debug_flag} -c {ck_dyn_src} -o {self.ck_dyn_obj}",
            logger=self.log,
        )
        self.log_info("%s", compile_cmd)
        with switch_directory(dirname):
            result, _, stderr = asyncio.get_event_loop().run_until_complete(
                compile_cmd.run_silent()
            )
        if result != 0:
            self.log_error("failed to compile %s to %s", ck_dyn_src, self.ck_dyn_obj)
            self.log_error("result: %s", result)
            for line in stderr:
                self.log_error(line.rstrip())

    def __repr__(self):
        return f"{self.__class__.__name__}"

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
        if restart:
            self.log_info("====== R E S T A R T ======")
        else:
            self.log_info("XXXXX S H U T D O W N XXXXX")
        for command in self._active_commands:
            self.log_info("kill %s", command)
            command.terminate()
        for filename in filter(os.path.isfile, (self.ck_dyn_obj,)):
            self.log_info("unlink %s", filename)
            os.unlink(filename)
        if os.path.isdir(self.twd):
            self.log_info("remove %s", self.twd)
            shutil.rmtree(self.twd)
        self.log_info("unlink trigger %s", self.stdin_trigger)
        self.stdin_trigger.close(unlink=True)
        return super().do_shutdown(restart)

    def do_interrupt(self):
        self.log_info("=== I N T E R R U P T ===")
        self.do_shutdown(restart=True)

    @contextmanager
    def active_command(self, command: AsyncCommand):
        """Add a command to the set of active commands while it is active"""
        self._active_commands.add(command)
        yield command
        try:
            self._active_commands.remove(command)
        except KeyError:
            self.log_info("active command not found: %s", command)

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

        self._allow_stdin = allow_stdin

        # Scan for magics
        if (
            len(code.splitlines()) == 1
            and (code.startswith("%") or code.startswith("!"))
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

        # Attempt to compile to .o. Do this silently at first, because if
        # successful we want to detect whether main was defined before
        # reporting the actual compilation command to the user
        compile_cmd = self.command_compile(
            args.compiler, args.cflags, args.LDFLAGS, args.filename, args.obj
        )
        self.debug_msg("attempt to compile to .o")
        self.log_info("attempt to compile to .o")
        result, _, stderr = await compile_cmd.run_silent()

        if result != 0:
            # failed to compile to .o, so report error
            self.debug_msg("failed!")
            self.log_info("failed!")
            for line in stderr:
                self.log_info(line.rstrip())
                self.print(line, dest=STDERR, end="")
            return error("CompileFailed", "Compilation failed")

        # compiled ok, continue to detect main
        self.debug_msg("detect whether main defined")

        result, *_ = await self.command_detect_main(args.obj).run_silent()
        if result != 0:
            # main not defined, so repeat to asynchronously report compilation
            # to .o and stop
            self.debug_msg("main not defined: compile to .o and stop")
            self.print(f"$> {compile_cmd}")
            compile_cmd = self.command_compile(
                args.compiler,
                args.cflags,
                args.LDFLAGS,
                args.filename,
                args.obj,
            )
            await compile_cmd.run_with_output(self.stream_stdout, self.stream_stderr)
            return success(self.execution_count)

        # main was defined, so compile & link in one command & report, then attempt to execute
        self.debug_msg("main was defined: attempt to compile and run executable")

        if args.language == Lang.C:
            extra_cflags = self.env.CKERNEL_EXE_CFLAGS or ""
        elif args.language == Lang.CPP:
            extra_cflags = self.env.CKERNEL_EXE_CXXFLAGS or ""
        else:
            extra_cflags = ""

        # report to the user the compilation command *without* the input wrappers
        compile_exe_cmd = self.command_compile_exe(
            args.compiler,
            extra_cflags + " " + args.cflags,
            (self.env.CKERNEL_EXE_LDFLAGS or "") + " " + args.LDFLAGS,
            args.filename,
            args.depends,
            args.exe,
        )
        self.print(f"$> {compile_exe_cmd}")

        # now add self.ck_dyn_obj to args.depends to add input wrappers
        compile_exe_cmd = self.command_compile_exe(
            args.compiler,
            extra_cflags + " " + args.cflags,
            (self.env.CKERNEL_EXE_LDFLAGS or "") + " " + args.LDFLAGS,
            args.filename,
            f"{self.ck_dyn_obj} " + args.depends,
            args.exe,
        )
        self.log_info(f"{compile_exe_cmd}")

        result, *_ = await compile_exe_cmd.run_with_output(
            self.stream_stdout, self.stream_stderr
        )
        if result != 0:
            return error("CompileFailed", "Compilation failed")
        if not args.should_exec:
            return success(self.execution_count)
        run_exe = AsyncCommand(f"./{args.exe} {args.ARGS}", logger=self.log)
        self.print(f"$> {run_exe}")
        with self.active_command(
            run_exe
        ) as command, self.stdin_trigger.ready() as trigger:
            result, *_ = await command.run_interactive(
                self.stream_stdout,
                self.stream_stderr,
                self.write_input,
                trigger,
            )
        if result != 0:
            self.print(f"executable failed with exit code {result}", dest=STDERR)
            return error("ExeFailed", "Executable failed")
        return success(self.execution_count)

    def parse_args(self, code: str) -> Namespace:
        args = self.default_compiler_args()
        header, *lines = code.splitlines()
        self.debug_msg(f"{header=}")
        assert header.startswith(self._tag_name)
        if header.startswith(self._tag_name):
            header = header[len(self._tag_name) :]
        args.filename = header.strip()
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
                if line.startswith(self._tag_opt):
                    line = line[len(self._tag_opt) :]
                opt, _, rest = line.strip().partition(" ")
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
            args.compiler = args.CC or self.env.CKERNEL_CC
        elif args.language == Lang.CPP:
            args.compiler = args.CXX or self.env.CKERNEL_CXX
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
        return AsyncCommand(f"{compiler} {cflags} {name} {depends} {ldflags} -o {exe}")

    def command_detect_main(self, objfile: str) -> AsyncCommand:
        if is_macOS:
            # it seems that on macOS `int main()` is compiled to the symbol
            # `_main`
            cmd = f"""nm {objfile} | grep " T _main" """
        else:
            cmd = f"""nm {objfile} | grep " T main" """
        return AsyncCommand(cmd)

    def command_link_exe(
        self, compiler: str, ldflags: str, exe: str, objname: str, depends: str
    ) -> AsyncCommand:
        return AsyncCommand(f"{compiler} {depends} {objname} {ldflags} -o {exe}")

    @classmethod
    def default_compiler_args(cls, extra: Optional[List[str]] = None) -> Namespace:
        "Return a namespace with known (and any extra) options set to an empty string"
        extra = extra or []
        args = Namespace(**{opt: "" for opt in (cls._known_opts + extra)})
        args.verbose = False
        return args

    @property
    def banner(self) -> str:
        extra = "\n\nEnvironment variables:\n"
        for name, value in self.env._asdict().items():
            extra = extra + f"\n{name}: {value}"
        return super().banner + extra
