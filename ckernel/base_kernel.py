"""Implements BaseKernel"""

import os
from asyncio import StreamReader, StreamWriter
from typing import Coroutine

from ipykernel.ipkernel import IPythonKernel

from .util import STDERR, STDOUT, Stream, Trigger


class BaseKernel(IPythonKernel):
    """Common functionality for our kernels"""

    language = "c"
    language_version = "C11"
    language_info = {
        "name": "c",
        "codemirror_mode": "text/x-csrc",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = os.getenv("CKERNEL_DEBUG") is not None

    @property
    def banner(self):
        return "\n".join(
            [
                "A basic Jupyter kernel which provides C/C++ syntax highlighting",
                "and a little more magic",
                "",
                "Copyright (c) 2023, Adam Tuft",
                "",
                "github.com/adamtuft/c-kernel",
            ]
        )

    async def stream_data(
        self, dest: Stream, reader: StreamReader, end: str = ""
    ) -> None:
        """Decode and stream data from reader to dest"""
        async for data in reader:
            self.print(data.decode(), dest=dest, end=end)

    def stream_stdout(self, reader: StreamReader) -> Coroutine[None, None, None]:
        """Return a coroutine which streams data from reader to stdout"""
        return self.stream_data(STDOUT, reader, end="")

    def stream_stderr(self, reader: StreamReader) -> Coroutine[None, None, None]:
        """Return a coroutine which streams data from reader to stderr"""
        return self.stream_data(STDERR, reader, end="")

    def write_input(
        self, writer: StreamWriter, input_trigger: Trigger, prompt: str = ""
    ):
        """Get input and send to writer. Wait for input request from input_trigger"""
        while True:
            input_trigger.wait()
            data = (
                self.raw_input(prompt=prompt) + "\n"
            )  # add a newline because self.raw_input does not
            writer.write(data.encode())

    def print(self, text: str, dest: Stream = STDOUT, end: str = "\n"):
        """Print to the kernel's stream dest"""
        self.send_response(
            self.iopub_socket, "stream", {"name": dest, "text": text + end}
        )

    def debug_msg(self, text: str):
        if self.debug:
            self.print(f"[DEBUG] {text}", dest=STDERR)
