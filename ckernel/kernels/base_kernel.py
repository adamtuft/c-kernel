from ipykernel.ipkernel import IPythonKernel


class BaseKernel(IPythonKernel):
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
