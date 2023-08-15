"""ckernel module __init__.py"""

__version__ = "0.2.0"

from . import async_kernel, autocompile_kernel, base_kernel, resource

kernels = {
    "AsyncKernel": async_kernel.AsyncKernel,
    "AutoCompileKernel": autocompile_kernel.AutoCompileKernel,
}


def class_list() -> list[str]:
    """Get the list of available kernel classes"""
    return list(kernels.keys())


def get_cls(kernel: str) -> base_kernel.BaseKernel:
    """Look up a kernel class by its name"""
    return kernels[kernel]


__all__ = ["get_cls", "class_list"]
