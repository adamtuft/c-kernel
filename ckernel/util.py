"""ckernel utilities"""

from __future__ import annotations

import asyncio
import os
import traceback
from contextlib import contextmanager
from enum import Enum
from functools import partial
from logging import Logger
from typing import Callable, Coroutine, NoReturn, Optional, Protocol
from uuid import uuid1 as uuid

from ipcqueue.posixmq import Queue as PosixMQ
from ipcqueue.serializers import RawSerializer


def debug(logger: Optional[Logger], name: str, msg: str, *args) -> None:
    if logger:
        logger.debug("[%s] " + msg, name, *args)


class Trigger:
    """Block until a process signals that it is ready"""

    def __init__(
        self, timeout: Optional[int] = None, logger: Optional[Logger] = None
    ) -> None:
        self._name = "/" + str(uuid())
        self._debug = partial(debug, logger, self.__class__.__name__)
        self._debug("%s created", self.name)
        self.timeout = timeout

    @property
    def name(self) -> str:
        return self._name

    def wait(self):
        """Block until ready to trigger"""
        self._debug("%s wait", self.name)
        self._mq.get(timeout=self.timeout)

    def start(self):
        self._debug("%s start", self.name)
        self._mq = PosixMQ(self._name, serializer=RawSerializer)

    def stop(self, unlink: bool = True):
        self._debug("%s stop", self.name)
        self._mq.close()
        if unlink:
            self._mq.unlink()

    @contextmanager
    def ready(self, unlink: bool = True):
        self.start()
        yield
        self.stop(unlink=unlink)


class StreamConsumer(Protocol):
    def __call__(self, reader: asyncio.StreamReader) -> Coroutine[None, None, None]:
        ...


class StreamWriter(Protocol):
    def __call__(
        self, writer: asyncio.StreamWriter, trigger: Trigger, prompt: str = ""
    ) -> NoReturn:
        ...


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

    def __init__(self, command: str, logger: Optional[Logger] = None) -> None:
        self._command: str = command
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._log: Optional[Logger] = logger
        self._debug = partial(debug, logger, self.__class__.__name__)
        self._stdin_trigger = Trigger(logger=self._log)

    @property
    def string(self) -> str:
        """show the command"""
        return self._command

    async def run(
        self: AsyncCommand,
        stdout: Optional[StreamConsumer] = None,
        stderr: Optional[StreamConsumer] = None,
        stdin: Optional[StreamWriter] = None,
    ) -> int:
        """run the command, streaming output via stdout and stderr arguments"""

        env = os.environ.copy()
        env["CK_MQNAME"] = self._stdin_trigger.name
        self._debug("env['CK_MQNAME']=%s", env["CK_MQNAME"])

        self._proc = await asyncio.create_subprocess_shell(
            self._command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            env=env,
            bufsize=0,
        )

        if stdin is not None:
            request_input = partial(
                stdin, self._proc.stdin, self._stdin_trigger, prompt="stdin: "
            )
            with self._stdin_trigger.ready(), self._cancelling_task(request_input):
                result = await self._await_subprocess(self._proc, stdout, stderr)
        else:
            result = await self._await_subprocess(self._proc, stdout, stderr)

        return result

    async def _await_subprocess(
        self,
        proc: asyncio.subprocess.Process,
        stdout: Optional[StreamConsumer],
        stderr: Optional[StreamConsumer],
    ) -> int:
        streams = []
        if stdout is not None:
            streams.append(stdout(proc.stdout))
        if stderr is not None:
            streams.append(stderr(proc.stderr))

        self._debug("wait for subprocess")
        await asyncio.gather(*streams, proc.wait())
        self._debug("subprocess complete")
        return proc.returncode

    @contextmanager
    @staticmethod
    def _cancelling_task(func: Callable):
        task = asyncio.get_running_loop().run_in_executor(None, func)
        yield task
        task.cancel()

    def terminate(self) -> None:
        """Terminate the subprocess"""
        self._debug("terminate process: %s", self._proc)
        if self._proc is not None:
            self._proc.terminate()
        self._stdin_trigger.stop()
