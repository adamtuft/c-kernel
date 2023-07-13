import asyncio
import json
from typing import Literal, Dict

from .base_kernel import BaseKernel

_compiler: str = None

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


class AutoCompileKernel(BaseKernel):
    """Auto compile C/C++ cells"""

    _tag_name = "////"
    _tag_opt =  "//%"
    _known_opts = [
        "CC",
        "CFLAGS",
        "LDFLAGS",
        "V"
    ]

    async def do_execute(self, code: str, silent, store_history=True, user_expressions=None, allow_stdin=False, cell_id=None):
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
                - //%V (to show the compiler command that will be executed)

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
            self.send_text("stderr", f"Cell must start with \"{self._tag_name} [name]\"\n")
            return {
                "status": "error",
                "ename": "NotNames",
                "evalue": f"Cell must start with \"{self._tag_name} [name]\"",
                "traceback": []
            }
        
        args = self.parse_args(code)
        self.send_text("stderr", json.dumps(args, indent=2) + "\n")
        self.send_text("stderr", f"command: {self.prepare_command(args)}\n")
        self.send_text("stdout", f"compiled {args['obj']}\n")
        return {"status": "ok", "execution_count": self.execution_count}

    def parse_args(self, code: str):
        args = {}
        header, *lines = code.splitlines()
        assert header.startswith(self._tag_name)
        args["name"] = header.removeprefix(self._tag_name).strip()
        args["obj"] = args["name"].split(".")[0] + ".o"
        for k, line in enumerate(lines, start=2):
            if line.startswith(self._tag_opt) and len(line.rstrip()) > len(self._tag_opt):
                opt, *val = line.removeprefix(self._tag_opt).split()
                if opt not in self._known_opts:
                    self.send_text("stderr", f"unknown option on line {k}: {opt}\n")
                else:
                    args[opt] = val
        return args
    
    def prepare_command(self, args) -> str:
        return f"""{args.get("CC", "cc")} {args.get("CFLAGS", "")} {args.get("LDFLAGS", "")} -c {args["name"]} -o {args["obj"]}"""

    # Some functions that would be useful as line magic (somehow):

    @staticmethod
    def compiler(*args, **kwargs):
        global _compiler
        return "whatever the compiler is, or set it and report that it was changed"

    @staticmethod
    def help(*args, **kwargs):
        return "some useful help string"
    
    @classmethod
    def options(cls, *args, **kwargs):
        return cls._known_opts
