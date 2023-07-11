from ipykernel.ipkernel import IPythonKernel


class BaseKernel(IPythonKernel):
    language = 'c'
    language_version = 'C11'
    language_info = {
        "name": "c",
        "codemirror_mode": "text/x-csrc",
    }
