"""Implements BaseKernel"""

from typing import Coroutine
from asyncio import StreamReader
from ipykernel.ipkernel import IPythonKernel

from .util import Stream, STDOUT, STDERR


class BaseKernel(IPythonKernel):
    """Common functionality for our kernels"""

    language = "c"
    language_version = "C11"
    language_info = {
        "name": "c",
        "codemirror_mode": "text/x-csrc",
    }

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

    def print(self, text: str, dest: Stream = STDOUT, end: str = "\n"):
        """Print to the kernel's stream dest"""
        self.send_response(
            self.iopub_socket, "stream", {"name": dest, "text": text + end}
        )
