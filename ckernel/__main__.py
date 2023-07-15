if __name__ == '__main__':
    import argparse
    import ckernel
    from ipykernel.kernelapp import IPKernelApp
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", choices=ckernel.names())
    parser.add_argument("CC", help="The C compiler to use with this kernel")
    parser.add_argument("CXX", help="The C++ compiler to use with this kernel")
    parser.add_argument("-f", help="The connection file to use")
    args = parser.parse_args()
    kernel_class = ckernel.get_kernel(args.kernel)
    kernel_class.ckargs = args
    IPKernelApp.launch_instance(kernel_class=kernel_class)
