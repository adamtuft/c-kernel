"""ckernel utilities"""
from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager
from functools import partial
from logging import Logger
from typing import Optional, Coroutine, NoReturn, Protocol

from .log import log_info
from .trigger import Trigger


class StreamConsumer(Protocol):
    def __call__(self, reader: asyncio.StreamReader) -> Coroutine[None, None, None]:
        ...


class StreamWriter(Protocol):
    def __call__(
        self, writer: asyncio.StreamWriter, trigger: Trigger, prompt: str = ""
    ) -> NoReturn:
        ...


class AsyncCommand:
    """Run an async command, streaming its stdout and stderr as directed."""

    def __init__(self, command: str, logger: Optional[Logger] = None) -> None:
        self.log_info = log_info(logger, self.__class__.__name__)
        self._command: str = command
        self._proc: Optional[asyncio.subprocess.Process] = None

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
            env[stdin_trigger.env_key] = stdin_trigger.name
            self.log_info(
                "env['%s']=%s", stdin_trigger.env_key, env[stdin_trigger.env_key]
            )

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
