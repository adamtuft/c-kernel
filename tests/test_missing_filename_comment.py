import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
import os
import pytest

def test_missing_filename_comment(installed_kernel):
    notebook_path = os.path.join("data", "test_missing_filename_comment.ipynb")
    expected_error = '[ERROR] code cell must start with "//// [filename]"'

    # Load the notebook
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # Run the notebook and check for the expected error
    client = NotebookClient(nb, timeout=60, kernel_name=installed_kernel)

    with pytest.raises(CellExecutionError) as excinfo:
        client.execute()

    # Assert the error message is present in the exception text
    assert expected_error in str(excinfo.value), (
        f'Expected error message "{expected_error}" in exception, got: {excinfo.value!r}'
    )
