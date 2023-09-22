"""Install and launch kernels"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import pathlib
import shlex
import shutil
import sys
import tempfile
import typing
from enum import Enum
from typing import Dict, List, TypedDict, Optional

import colorama
import jupyter_client
from ipykernel.kernelapp import IPKernelApp

import ckernel
from ckernel.autocompile_kernel import AutoCompileKernel

KernelSpec = TypedDict(
    "KernelSpec",
    {
        "argv": List[str],
        "display_name": str,
        "env": Dict[str, str],
        "interrupt_mode": str,
    },
)

InstallResult = TypedDict("InstallResult", {"dest": str, "spec": KernelSpec})


class Command(Enum):
    """Constants for the known commands"""

    INSTALL = "install"
    RUN = "run"
    SHOW = "show"


@contextlib.contextmanager
def tempdir():
    """Yield a temporary directory which is auto-deleted after use"""
    tdir = pathlib.Path(tempfile.mkdtemp())
    yield tdir
    shutil.rmtree(tdir)


def install(
    specdir: pathlib.Path,
    name: str,
    display_name: str,
    user: bool,
    prefix: str,
    c_compiler: str,
    cpp_compiler: str,
    debug: bool,
    env: Optional[Dict[str, str]] = None,
) -> InstallResult:
    """Install a specific kernel"""

    ksm = jupyter_client.kernelspec.KernelSpecManager()

    # The kernel spec to serialise in "kernel.json"
    spec = KernelSpec(
        argv=shlex.split(f"python3 -m ckernel run" + " -f {connection_file}"),
        display_name=display_name or "AutoCompileKernel",
        env={
            "CKERNEL_CC": c_compiler,
            "CKERNEL_CXX": cpp_compiler,
        },
        interrupt_mode="message",
    )
    if debug:
        spec["env"]["CKERNEL_DEBUG"] = "TRUE"

    if env:
        spec["env"].update(env)

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
    dest = str(dest)

    for prog in [c_compiler, cpp_compiler]:
        if shutil.which(prog) is None:
            print(
                colorama.Fore.RED
                + f"WARNING: {prog} not found in your PATH. "
                + "Please ensure it's available before using this kernel."
                + colorama.Style.RESET_ALL,
                file=sys.stderr,
            )

    return InstallResult(dest=dest, spec=spec)


def install_startup_script(name: str, installdir: str, spec: KernelSpec, script: str):
    kernel_start_path = ckernel.resource.get("kernel.sh")
    with open(kernel_start_path, "r", encoding="utf-8") as kernel_start_file:
        kernel_start = "".join(kernel_start_file.readlines())
        kernel_start = kernel_start.format(
            name=name, installdir=installdir, script=script
        )

    startup_script_path = os.path.abspath(pathlib.Path(installdir) / "kernel.sh")
    with open(startup_script_path, "w", encoding="utf-8") as startup_script:
        startup_script.write(kernel_start)
    os.chmod(startup_script_path, 0o744)

    spec["argv"] = shlex.split(f"{startup_script_path} {{connection_file}}")

    with open(
        pathlib.Path(installdir) / "kernel.json", "w", encoding="utf-8"
    ) as specfile:
        json.dump(spec, specfile, indent=4)


def show(name: str):
    """Print the path to some resource"""
    path = ckernel.resource.get(name)
    if path is None:
        raise SystemExit(1)
    print(path)


def main(prog: typing.Optional[str] = None) -> None:
    """Install or run a kernel"""

    formatter_class = argparse.ArgumentDefaultsHelpFormatter

    install_help = "install a kernel"
    run_help = "run an installed kernel"
    show_help = "print various source or resource paths"

    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument("-v", "--version", help="print version", action="store_true")

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
        "name", help="a name for this kernel (must be unique among installed kernels)"
    )
    parse_install.add_argument(
        "display_name", help="name to display in Jupyter", metavar="display-name"
    )
    parse_install.add_argument(
        "--cc",
        help="the C compiler which this kernel should use",
        default="gcc",
    )
    parse_install.add_argument(
        "--cxx",
        help="the C++ compiler which this kernel should use",
        default="g++",
    )
    parse_install.add_argument(
        "--exe-cflags",
        help="CFLAGS to pass when compiling/linking executables",
        dest="exe_cflags",
        metavar="CFLAGS",
    )
    parse_install.add_argument(
        "--exe-cxxflags",
        help="CXXFLAGS to pass when compiling/linking executables",
        dest="exe_cxxflags",
        metavar="CXXFLAGS",
    )
    parse_install.add_argument(
        "--exe-ldflags",
        help="LDFLAGS to pass when compiling/linking executables",
        dest="exe_ldflags",
        metavar="LDFLAGS",
    )
    parse_install.add_argument(
        "--user", action="store_true", help="install per-user only"
    )
    parse_install.add_argument(
        "--prefix", help="install under {prefix}/share/jupyter/kernels", metavar="path"
    )
    parse_install.add_argument(
        "--debug",
        action="store_true",
        help="kernel reports debug messages to notebook user",
    )
    parse_install.add_argument(
        "--startup",
        metavar="script",
        help="a startup script to be sourced before launching the kernel",
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
        "-f", help="the connection file to use", metavar="connection"
    )

    # Parse the show subcommand
    parse_show = command_action.add_parser(
        Command.SHOW.value,
        help=show_help,
        description=show_help,
        formatter_class=formatter_class,
    )

    # Arguments to the show subcommand
    parse_show.add_argument(
        "name",
        metavar="name",
        help="the name of the resource to show, or 'include' to print all internal include paths",
    )

    args = parser.parse_args()

    if args.version:
        print(ckernel.__version__)
        raise SystemExit(0)

    args.command = Command(args.command)
    if args.command == Command.INSTALL:
        env = {}
        if args.exe_cflags:
            env["CKERNEL_EXE_CFLAGS"] = args.exe_cflags
        if args.exe_cxxflags:
            env["CKERNEL_EXE_CXXFLAGS"] = args.exe_cxxflags
        if args.exe_ldflags:
            env["CKERNEL_EXE_LDFLAGS"] = args.exe_ldflags
        with tempdir() as specdir:
            installed = install(
                specdir,
                args.name,
                args.display_name,
                args.user,
                args.prefix,
                args.cc,
                args.cxx,
                args.debug,
                env=env,
            )
            print(
                f'installed {args.name} (display name "{args.display_name}") at {installed["dest"]}'
            )
        if args.startup:
            install_startup_script(
                args.name,
                installed["dest"],
                installed["spec"],
                args.startup,
            )
    elif args.command == Command.RUN:
        IPKernelApp.launch_instance(kernel_class=AutoCompileKernel)
    elif args.command == Command.SHOW:
        show(args.name)
    else:
        print(
            colorama.Fore.RED
            + f"ERROR: unknown acation: {args.command.value}"
            + colorama.Style.RESET_ALL
        )
        parser.print_help()
