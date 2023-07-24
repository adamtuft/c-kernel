"""ckernel module __init__.py"""

from . import base_kernel
from . import async_kernel
from . import autocompile_kernel

kernels = {
    "AsyncKernel": async_kernel.AsyncKernel,
    "AutoCompileKernel": autocompile_kernel.AutoCompileKernel,
}


def kernel_names() -> list[str]:
    """Get the list of available kernel classes"""
    return list(kernels.keys())


def get_kernel(kernel: str) -> base_kernel.BaseKernel:
    """Look up a kernel class by its name"""
    return kernels[kernel]


__all__ = ["get_kernel", "kernel_names"]
