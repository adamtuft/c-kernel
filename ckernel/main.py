"""Install and launch kernels"""

import sys
import typing
import pathlib
import tempfile
import shutil
import contextlib
import argparse
import json
from enum import Enum

import colorama
import jupyter_client
from ipykernel.kernelapp import IPKernelApp

import ckernel


class Command(Enum):
    """Constants for the known commands"""

    INSTALL = "install"
    RUN = "run"


@contextlib.contextmanager
def tempdir():
    """Yield a temporary directory which is auto-deleted after use"""
    tdir = pathlib.Path(tempfile.mkdtemp())
    yield tdir
    shutil.rmtree(tdir)


def install(
    specdir: pathlib.Path,
    kernel: str,
    name: str,
    display_name: str,
    user: bool,
    prefix: str,
    c_compiler: str,
    cpp_compiler: str,
) -> None:
    """Install a specific kernel"""

    for prog in [c_compiler, cpp_compiler]:
        location = shutil.which(prog)
        if location is None:
            print(
                colorama.Fore.RED
                + f"WARNING: {prog} not found in your PATH. "
                + "Please ensure it's available before using this kernel."
                + colorama.Style.RESET_ALL,
                file=sys.stderr,
            )
        else:
            print(f"found {prog}: {location}")

    ksm = jupyter_client.kernelspec.KernelSpecManager()

    # The kernel spec to serialise in "kernel.json"
    spec = dict()
    spec["argv"] = (
        f"python3 -m ckernel run {kernel}" + " -f {connection_file}"
    ).split()
    spec["display_name"] = display_name or kernel
    spec["env"] = {"CKERNEL_CC": c_compiler, "CKERNEL_CXX": cpp_compiler}

    with open(specdir / pathlib.Path("kernel.json"), "w", encoding="utf-8") as specfile:
        json.dump(spec, specfile, indent=4)

    install_args = {
        "kernel_name": name,
        "user": user,
        "prefix": prefix,
    }

    try:
        dest = ksm.install_kernel_spec(str(specdir), **install_args)
    except PermissionError as err:
        print(f"{type(err).__name__}: {err}")
        print("Kernel installation failed, trying again with --user")
        install_args["user"] = True
        dest = ksm.install_kernel_spec(str(specdir), **install_args)
    print(f'installed {kernel} as {name} (display name "{display_name}") at {dest}')


def main(prog: typing.Optional[str] = None) -> None:
    """Install or run a kernel"""

    formatter_class = argparse.ArgumentDefaultsHelpFormatter

    install_help = "install a kernel"
    run_help = "run an installed kernel"

    parser = argparse.ArgumentParser(prog=prog)

    command_action = parser.add_subparsers(dest="command", metavar="action")

    # Parse the install subcommand
    parse_install = command_action.add_parser(
        Command.INSTALL.value,
        help=install_help,
        description=install_help,
        formatter_class=formatter_class,
    )

    # Arguments to the install subcommand
    parse_install.add_argument(
        "kernel",
        help=f"kernel to install ({', '.join(ckernel.class_list())})",
        choices=ckernel.class_list(),
        metavar="kernel",
    )
    parse_install.add_argument(
        "name", help="a name for this kernel (must be unique among installed kernels)"
    )
    parse_install.add_argument(
        "display_name", help="name to display in Jupyter", metavar="display-name"
    )
    parse_install.add_argument(
        "--cc",
        help="the C compiler which this kernel should use",
        default="/usr/bin/gcc",
    )
    parse_install.add_argument(
        "--cxx",
        help="the C++ compiler which this kernel should use",
        default="/usr/bin/g++",
    )
    parse_install.add_argument(
        "--user", action="store_true", help="install per-user only"
    )
    parse_install.add_argument(
        "--prefix", help="install under {prefix}/share/jupyter/kernels", metavar="path"
    )

    # Parse the run subcommand
    parse_run = command_action.add_parser(
        Command.RUN.value,
        help=run_help,
        description=run_help,
        formatter_class=formatter_class,
    )

    # Arguments to the run subcommand
    parse_run.add_argument(
        "kernel",
        metavar="kernel",
        help="the class of the kernel to run",
    )
    parse_run.add_argument(
        "-f", help="the connection file to use", metavar="connection"
    )

    args = parser.parse_args()
    args.command = Command(args.command)

    if args.command == Command.INSTALL:
        with tempdir() as specdir:
            install(
                specdir,
                args.kernel,
                args.name,
                args.display_name,
                args.user,
                args.prefix,
                args.cc,
                args.cxx,
            )
    elif args.command == Command.RUN:
        IPKernelApp.launch_instance(kernel_class=ckernel.get_cls(args.kernel))
    else:
        print(
            colorama.Fore.RED
            + f"ERROR: unknown acation: {args.command.value}"
            + colorama.Style.RESET_ALL
        )
        parser.print_help()
