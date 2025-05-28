import subprocess
import sys
import json
import random
import string

def random_kernel_name(prefix="ckernel-test-"):
    # Always append a random 6-character alphanumeric suffix to the prefix
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return prefix + suffix

def assert_kernel_installed(kernel_name, display_name="C/C++"):
    install_cmd = [
        sys.executable, "-m", "ckernel", "install", kernel_name, display_name
    ]
    result = subprocess.run(
        install_cmd, capture_output=True, text=True
    )
    assert result.returncode == 0, f"Install failed: {result.stderr}"

def assert_kernel_discovered(kernel_name, display_name="C/C++"):
    list_cmd = ["jupyter", "kernelspec", "list", "--json"]
    result = subprocess.run(
        list_cmd, capture_output=True, text=True
    )
    assert result.returncode == 0, f"Failed to list kernels: {result.stderr}"
    kernels = json.loads(result.stdout)["kernelspecs"]
    assert kernel_name in kernels, f"Kernel '{kernel_name}' not found in Jupyter kernels: {result.stdout}"
    assert kernels[kernel_name]["spec"]["display_name"] == display_name, \
        f"Kernel display name does not match: {kernels[kernel_name]['spec']['display_name']}"

def assert_kernel_uninstalled(kernel_name):
    remove_cmd = ["jupyter", "kernelspec", "remove", "-y", kernel_name]
    result = subprocess.run(
        remove_cmd, capture_output=True, text=True
    )
    assert result.returncode == 0, f"Failed to remove kernel: {result.stderr}"

    # Confirm the kernel is removed
    list_cmd = ["jupyter", "kernelspec", "list", "--json"]
    result = subprocess.run(
        list_cmd, capture_output=True, text=True
    )
    assert result.returncode == 0, f"Failed to list kernels after removal: {result.stderr}"
    kernels = json.loads(result.stdout)["kernelspecs"]
    assert kernel_name not in kernels, f"Kernel '{kernel_name}' still present after removal."

def test_kernel_lifecycle(installed_kernel):
    kernel_name = random_kernel_name()
    try:
        assert_kernel_installed(kernel_name)
        assert_kernel_discovered(kernel_name)
    finally:
        assert_kernel_uninstalled(kernel_name)

