from .async_kernel import AsyncKernel
from .autocompile_kernel import AutoCompileKernel

_kernels = {
    "AsyncKernel": AsyncKernel,
    "AutoCompileKernel": AutoCompileKernel
}

def names() -> list[str]:
    return list(_kernels.keys())

def get_kernel(kernel: str):
    return _kernels.get(kernel)

__all__ = [
    "get_kernel",
    "names"
]
