from contextlib import contextmanager

@contextmanager
def tempdir():
    import pathlib, tempfile, shutil
    d = pathlib.Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d)

def install() -> None:
    from argparse import ArgumentParser
    from json import dump
    from jupyter_client.kernelspec import KernelSpecManager
    from ckernel import kernel_names
    parser = ArgumentParser()
    parser.add_argument("kernel", help="Kernel to install", choices=kernel_names())
    parser.add_argument("name", help="The name for this kernel (must be unique among installed kernels)")
    parser.add_argument("display_name", help="Kernel name to display in Jupyter")
    parser.add_argument("--cc", help="The C compiler which this kernel should use", default="cc")
    parser.add_argument("--cxx", help="The C++ compiler which this kernel should use", default="cpp")
    parser.add_argument("--user", action="store_true", help="Install per-user instead of system-wide.")
    parser.add_argument("--prefix", help="Install under {prefix}/share/jupyter/kernels")
    args = parser.parse_args()
    ksm = KernelSpecManager()
    with tempdir() as specdir:
        spec = dict()
        spec["argv"] = (f"python3 -m ckernel {args.kernel} {args.cc} {args.cxx}" + " -f {connection_file}").split()
        spec["display_name"] = args.display_name or args.kernel
        with open(specdir / "kernel.json", "w") as specfile:
            dump(spec, specfile, indent=4)
        spec_args = {"kernel_name": args.name, "user": args.user, "prefix": args.prefix}
        try:
            dest = ksm.install_kernel_spec(str(specdir), **spec_args)
        except PermissionError as err:
            print(f"{type(err).__name__}: {err}")
            print("Kernel installation failed, trying again with --user")
            spec_args["user"] = True
            dest = ksm.install_kernel_spec(str(specdir), **spec_args)
        print(f"installed {args.kernel} as {args.name} (display name \"{args.display_name}\") at {dest}")
