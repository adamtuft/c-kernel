import pytest
import tempfile
import os
import shutil
import subprocess
import sys
import random
import string
import json

@pytest.fixture(scope="session", autouse=True)
def temp_working_dir():
    """
    Set the working directory to the tests directory for the session.
    After all tests, remove all non-.py files and directories using git clean.
    """
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    orig_dir = os.getcwd()
    os.chdir(tests_dir)
    try:
        yield
    finally:
        # Remove all non-.py files and directories in tests/ using git clean
        # -f: force, -d: directories, -X: ignored files, -x: also untracked files
        # But we want to keep *.py files, so we use -e to exclude them
        subprocess.run(
            ["git", "clean", "-fdx", "-e", "*.py"],
            cwd=tests_dir,
            check=True
        )
        os.chdir(orig_dir)

def random_kernel_name(prefix="ckernel-test-"):
    # Always append a random 6-character alphanumeric suffix to the prefix
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return prefix + suffix

@pytest.fixture(scope="session")
def installed_kernel():
    """Fixture that installs a random ckernel-test kernel for all tests and removes it at the end."""
    kernel_name = random_kernel_name()
    display_name = "C/C++"
    install_cmd = [
        sys.executable, "-m", "ckernel", "install", kernel_name, display_name
    ]
    remove_cmd = ["jupyter", "kernelspec", "remove", "-y", kernel_name]

    # Install the kernel
    install_result = subprocess.run(
        install_cmd, capture_output=True, text=True
    )
    assert install_result.returncode == 0, f"Kernel install failed: {install_result.stderr}"

    # Confirm the kernel is in the list
    list_cmd = ["jupyter", "kernelspec", "list", "--json"]
    list_result = subprocess.run(
        list_cmd, capture_output=True, text=True
    )
    assert list_result.returncode == 0, f"Kernel list failed: {list_result.stderr}"
    kernels = json.loads(list_result.stdout)["kernelspecs"]
    assert kernel_name in kernels, f"Kernel '{kernel_name}' not found after install."

    yield kernel_name

    # Remove the kernel after all tests
    remove_result = subprocess.run(
        remove_cmd, capture_output=True, text=True
    )
    assert remove_result.returncode == 0, f"Kernel uninstall failed: {remove_result.stderr}"

    # Confirm removal
    list_result = subprocess.run(
        list_cmd, capture_output=True, text=True
    )
    kernels = json.loads(list_result.stdout)["kernelspecs"]
    assert kernel_name not in kernels, f"Kernel '{kernel_name}' still present after uninstall."
