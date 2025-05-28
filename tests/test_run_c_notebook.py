import nbformat
from nbclient import NotebookClient
import os

def test_notebook_prints_hello_world(installed_kernel):
    notebook_path = os.path.join("data", "test_c_code_cell.ipynb")
    expected_output = "hello, world!"

    # Load the notebook
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # Run the notebook using the kernel provided by the fixture
    client = NotebookClient(nb, timeout=60, kernel_name=installed_kernel)
    nb_executed = client.execute()

    # Collect all stdout from all code cell outputs
    cell_outputs = []
    for cell in nb_executed.cells:
        if cell.cell_type == "code":
            for output in cell.get("outputs", []):
                if output.output_type == "stream" and output.name == "stdout":
                    cell_outputs.append(output.text)

    # Join outputs and assert the expected string is present
    all_output = "".join(cell_outputs)
    assert expected_output in all_output, f'Expected "{expected_output}" in notebook output, got: {all_output!r}'

