if __name__ == '__main__':
    import argparse
    import ckernel
    from ipykernel.kernelapp import IPKernelApp
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", choices=ckernel.get_kernel.keys())
    parser.add_argument("-f", help="The connection file to use")
    args = parser.parse_args()
    IPKernelApp.launch_instance(kernel_class=ckernel.get_kernel[args.kernel])
