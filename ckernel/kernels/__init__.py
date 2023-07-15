from .base_kernel import BaseKernel
from .async_kernel import AsyncKernel
from .autocompile_kernel import AutoCompileKernel

kernels = {
    "AsyncKernel": AsyncKernel,
    "AutoCompileKernel": AutoCompileKernel
}

def kernel_names() -> list[str]:
    return list(kernels.keys())

def get_kernel(kernel: str) -> BaseKernel:
    return kernels[kernel]

__all__ = [
    "get_kernel",
    "kernel_names"
]
