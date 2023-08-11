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
from typing import Callable, Coroutine, NoReturn, Optional, Protocol
from uuid import uuid1 as uuid

from ipcqueue.posixmq import Queue as PosixMQ
from ipcqueue.serializers import RawSerializer


def temporary_directory(prefix: Optional[str] = None):
    "Return a temporary directory"
    return Path(mkdtemp(prefix=prefix))


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
        self, timeout: Optional[int] = None, logger: Optional[Logger] = None
    ) -> None:
        self._name = "/" + str(uuid())
        self.log_info = log_info(logger, self.__class__.__name__)
        self.log_info("%s created", self.name)
        self.timeout = timeout

    @property
    def name(self) -> str:
        return self._name

    def wait(self):
        """Block until ready to trigger"""
        self.log_info("%s wait", self.name)
        self._mq.get(timeout=self.timeout)

    def start(self):
        self.log_info("%s start", self.name)
        self._mq = PosixMQ(self._name, serializer=RawSerializer)

    def stop(self, unlink: bool = True):
        self.log_info("%s stop", self.name)
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

    # TODO: add option to return stdout & stderr instead of streaming somewhere

    def __init__(self, command: str, logger: Optional[Logger] = None) -> None:
        self.log_info = log_info(logger, self.__class__.__name__)
        self._command: str = command
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._stdin_trigger = Trigger(logger=logger)

    def __str__(self) -> str:
        return self._command

    @property
    def string(self) -> str:
        """show the command"""
        return str(self)

    async def run(
        self: AsyncCommand,
        stdout: Optional[StreamConsumer] = None,
        stderr: Optional[StreamConsumer] = None,
        stdin: Optional[StreamWriter] = None,
        **kwargs,
    ):
        """run the command, streaming output via stdout and stderr arguments.
        If either is None, return a list[str] for the corresponding stream."""

        kwargs["bufsize"] = kwargs.get("bufsize", 0)
        kwargs["env"] = kwargs.get("env", os.environ.copy())
        env = kwargs["env"]
        env["CK_MQNAME"] = self._stdin_trigger.name
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

        with self.prepare_stdin(stdin, self._proc.stdin, self._stdin_trigger):
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
            with stdin_trigger.ready(), self._cancelling_task(
                partial(stdin, proc_stdin, stdin_trigger, prompt="stdin: ")
            ):
                yield
        else:
            yield

    async def gather_data(self, lines: list[str], reader: asyncio.StreamReader) -> None:
        """Gather data into a list of str"""
        async for data in reader:
            lines.append(data.decode())

    @staticmethod
    @contextmanager
    def _cancelling_task(func: Callable):
        task = asyncio.get_running_loop().run_in_executor(None, func)
        yield task
        task.cancel()

    def terminate(self) -> None:
        """Terminate the subprocess"""
        self.log_info("terminate process: %s", self._proc)
        if self._proc is not None:
            self._proc.terminate()
        self._stdin_trigger.stop()
