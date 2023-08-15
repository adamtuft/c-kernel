"""ckernel utilities"""

from __future__ import annotations

import asyncio
import os
import traceback
from contextlib import contextmanager
from enum import Enum
from functools import partial
from logging import Logger
from pathlib import Path
from tempfile import mkdtemp
from typing import Coroutine, NoReturn, Optional, Protocol
from uuid import uuid1 as uuid

from ipcqueue.posixmq import Queue as PosixMQ
from ipcqueue.serializers import RawSerializer


def temporary_directory(prefix: Optional[str] = None):
    "Return a temporary directory"
    return Path(mkdtemp(prefix=prefix))


@contextmanager
def switch_directory(new: str):
    old = os.getcwd()
    os.chdir(new)
    yield
    os.chdir(old)


def log_info(log: Optional[Logger], prefix: str):
    "Send a prefixed info message"
    if log:

        def inner(msg: str, *args) -> None:
            log.info("[%s] " + msg, prefix, *args)

    else:

        def inner(*_) -> None:
            pass

    return inner


class Trigger:
    """Block until a process signals that it is ready"""

    def __init__(
        self,
        prefix: str = "",
        timeout: Optional[int] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        self._name = "/" + prefix + str(uuid())
        self.log_info = log_info(logger, self.__class__.__name__)
        self.log_info("%s created", self.name)
        self.timeout = timeout
        self._mq: Optional[PosixMQ] = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name}, timeout={self.timeout})"

    @property
    def is_ready(self):
        return self._mq is not None

    @property
    def name(self) -> str:
        return self._name

    def wait(self):
        """Block until ready to trigger"""
        self.log_info("%s wait", self.name)
        if self._mq is not None:
            return self._mq.get(timeout=self.timeout)

    def stop(self, unlink: bool = True):
        self.log_info("%s stop", self.name)
        if self._mq is not None:
            self._mq.close()
            if unlink:
                self._mq.unlink()

    @contextmanager
    def ready(self, unlink: bool = True):
        self.log_info("%s start", self.name)
        self._mq = PosixMQ(self._name, serializer=RawSerializer)
        yield self
        self.stop(unlink=unlink)
        self._mq = None


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

    # TODO: add option to return stdout & stderr instead of streaming somewhere

    def __init__(self, command: str, logger: Optional[Logger] = None) -> None:
        self.log_info = log_info(logger, self.__class__.__name__)
        self._command: str = command
        self._proc: Optional[asyncio.subprocess.Process] = None
        # self._stdin_trigger = Trigger(logger=logger)
        # self.log_info("created %s", self._stdin_trigger)

    def __str__(self) -> str:
        return self._command

    async def run_silent(self):
        return await self.run(None, None, None, None)

    async def run_with_output(self, stdout: StreamConsumer, stderr: StreamConsumer):
        return await self.run(stdout, stderr, None, None)

    async def run_interactive(
        self,
        stdout: StreamConsumer,
        stderr: StreamConsumer,
        stdin: StreamWriter,
        stdin_trigger: Trigger,
    ):
        return await self.run(stdout, stderr, stdin, stdin_trigger)

    async def run(
        self: AsyncCommand,
        stdout: Optional[StreamConsumer],
        stderr: Optional[StreamConsumer],
        stdin: Optional[StreamWriter],
        stdin_trigger: Optional[Trigger],
        **kwargs,
    ):
        """run the command, streaming output via stdout and stderr arguments.
        If either is None, return a list[str] for the corresponding stream."""

        if stdin is not None and stdin_trigger is None:
            raise ValueError("stdin_trigger may not be None when stdin is not None")

        if stdin_trigger is not None and not stdin_trigger.is_ready:
            raise ValueError("stdin_trigger must be ready")

        kwargs["bufsize"] = kwargs.get("bufsize", 0)
        kwargs["env"] = kwargs.get("env", os.environ.copy())
        if stdin_trigger is not None:
            env = kwargs["env"]
            env["CK_MQNAME"] = stdin_trigger.name
            self.log_info("env['CK_MQNAME']=%s", env["CK_MQNAME"])

        self._proc = await asyncio.create_subprocess_shell(
            self._command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            **kwargs,
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        stdout = stdout or partial(self.gather_data, stdout_lines)
        stderr = stderr or partial(self.gather_data, stderr_lines)

        with self.prepare_stdin(stdin, self._proc.stdin, stdin_trigger):
            await asyncio.gather(
                stdout(self._proc.stdout),
                stderr(self._proc.stderr),
                self._proc.wait(),
            )

        return self._proc.returncode, stdout_lines, stderr_lines

    @contextmanager
    def prepare_stdin(
        self,
        stdin: Optional[StreamWriter],
        proc_stdin: asyncio.StreamWriter,
        stdin_trigger: Trigger,
    ):
        if stdin is not None:
            func = partial(stdin, proc_stdin, stdin_trigger, prompt="stdin: ")
            task = asyncio.get_running_loop().run_in_executor(None, func)
            yield
            task.cancel()
        else:
            yield

    async def gather_data(self, lines: list[str], reader: asyncio.StreamReader) -> None:
        """Gather data into a list of str"""
        async for data in reader:
            lines.append(data.decode())

    def terminate(self) -> None:
        """Terminate the subprocess"""
        self.log_info("terminate process: %s", self._proc)
        if self._proc is not None:
            self._proc.terminate()
        # self._stdin_trigger.stop(unlink=True)
