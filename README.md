## About

An IPython kernel for teaching and learning C/C++ in a Jupyter notebook, providing C/C++ syntax highlighting and a little more magic.

This kernel extents the default IPython kernel to provide C/C++ syntax highlighting and the ability to execute shell commands embedded in comments when the cell contents are saved using the `%%file` cell magic:

<p align="center">
<img src="img/demo-1.png">
</p>

## Installation

To install from git:

```
git clone git@github.com:adamtuft/c-kernel.git
python3 -m pip install ./c-kernel
```

Then, to install the kernel use the `ckernel_install` command (see `ckernel_install --help` for all options) e.g.:

```
ckernel_install AsyncKernel "C/C++ Teaching"
```

The kernel will then be available under the given display name within Jupyter:

<p align="center">
<img src="img/demo-2.png">
</p>


## License

Licensed under the BSD 3-Clause License (see the [license file](LICENSE)).

Copyright (c) 2023, Adam Tuft
