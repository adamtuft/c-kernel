"""ckernel utilities"""

from __future__ import annotations
import traceback
import asyncio
from enum import Enum
from typing import Optional, Callable, Coroutine

StreamConsumer = Callable[[asyncio.StreamReader], Coroutine[None, None, None]]


class Stream(str, Enum):
    """Constants representing standard output channels"""

    STDERR = "stderr"
    STDOUT = "stdout"


STDERR = Stream.STDERR
STDOUT = Stream.STDOUT


class Lang(str, Enum):
    """Represents the recognised languages"""

    C = "C"
    CPP = "C++"


language = {
    "c": Lang.C,
    "cpp": Lang.CPP,
    "cxx": Lang.CPP,
    "cc": Lang.CPP,
}


def success(execution_count: int) -> dict[str, str | int]:
    """Construct a dict representing a success message"""
    return {"status": "ok", "execution_count": execution_count}


def error(
    ename: str, evalue: str, trace: Optional[list[str]] = None
) -> dict[str, str | list[str]]:
    """Construct a dict representing an error message"""
    return {
        "status": "error",
        "ename": ename,
        "evalue": evalue,
        "traceback": trace or [],
    }


def error_from_exception(exc_type, exc, tb):
    """Get the last traceback and return the message and an error dict"""
    tb_str = "\n".join(traceback.format_tb(tb))
    message = f"{tb_str}\n{exc_type.__name__}: {exc}"
    return message, error(exc_type.__name__, str(exc), traceback.format_tb(tb))


class AsyncCommand:
    """Run an async command, streaming its stdout and stderr as directed."""

    def __init__(self, command: str) -> None:
        self._command: str = command

    @property
    def string(self) -> str:
        """show the command"""
        return self._command

    async def run(
        self: AsyncCommand,
        stdout: Optional[StreamConsumer] = None,
        stderr: Optional[StreamConsumer] = None,
    ) -> int:
        """run the command, streaming output via stdout and stderr arguments"""
        proc = await asyncio.create_subprocess_shell(
            self._command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        streams = []
        if stdout is not None:
            streams.append(stdout(proc.stdout))
        if stderr is not None:
            streams.append(stderr(proc.stderr))
        await asyncio.gather(*streams, proc.wait())
        return proc.returncode
