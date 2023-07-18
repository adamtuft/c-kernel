from typing import Literal
from argparse import Namespace
from ipykernel.ipkernel import IPythonKernel

Stream = Literal["stderr", "stdout"]
STDERR: Stream = "stderr"
STDOUT: Stream = "stdout"


class BaseKernel(IPythonKernel):
    ckargs: Namespace = Namespace()
    language = 'c'
    language_version = 'C11'
    language_info = {
        "name": "c",
        "codemirror_mode": "text/x-csrc",
    }

    @property
    def banner(self):
        return "\n".join([
            "A basic Jupyter kernel which provides C/C++ syntax highlighting",
            "and a little more magic",
            "",
            "Copyright (c) 2023, Adam Tuft",
            "",
            "github.com/adamtuft/c-kernel"
        ])

    # def send_text(self, name: Stream, text: str):
    #     self.send_response(self.iopub_socket, 'stream', {'name': name, 'text': text})

    def print(self, text: str, dest: Stream = STDOUT, end: str = "\n"):
        self.send_response(self.iopub_socket, 'stream', {'name': dest, 'text': text + end})
