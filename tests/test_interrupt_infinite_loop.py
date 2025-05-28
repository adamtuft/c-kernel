import nbformat
import pytest
from nbclient import NotebookClient
from nbclient.exceptions import DeadKernelError

def test_kernel_interrupt_and_dead_kernel(installed_kernel):
    nb = nbformat.read(open("data/test_infinite_loop.ipynb"), as_version=4)
    client = NotebookClient(
        nb,
        timeout=3,
        kernel_name=installed_kernel,
        interrupt_on_timeout=True,
    )
    with pytest.raises(DeadKernelError):
        client.execute()