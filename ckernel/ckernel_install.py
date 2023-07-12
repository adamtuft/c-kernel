def install() -> None:
    try:
        import importlib.resources as resources
    except ImportError:
        import importlib_resources as resources
    import os
    import argparse
    import ckernel
    import json
    from jupyter_client.kernelspec import KernelSpecManager
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", choices=ckernel.get_kernel.keys(), help="Which kernel to install")
    parser.add_argument("display_name", help="Kernel name to display in Jupyter")
    parser.add_argument("--user", action="store_true", help="Install per-user instead of system-wide.")
    parser.add_argument("--prefix", help="Install under {prefix}/share/jupyter/kernels")
    args = parser.parse_args()
    spec = dict()
    spec["argv"] = ("python3 -m ckernel " + args.kernel + " -f {connection_file}").split()
    spec["display_name"] = args.display_name or args.kernel
    specdir = resources.files(ckernel) / f"_spec_{args.kernel.lower()}"
    if not specdir.is_dir():
        os.mkdir(specdir)
    with open(specdir / "kernel.json", "w") as specfile:
        json.dump(spec, specfile, indent=4)
    destination = KernelSpecManager().install_kernel_spec(str(specdir), kernel_name=args.kernel, user=args.user, prefix=args.prefix)
    print(f"installed {args.kernel} (display_name=\"{args.display_name}\") at {destination}")
