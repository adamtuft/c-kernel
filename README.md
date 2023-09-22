# c-kernel

<p align="center">
<a href="https://c-kernel.readthedocs.io/en/latest/index.html"><img src="https://readthedocs.org/projects/c-kernel/badge/"></a>
<a href="https://pypi.org/project/ckernel/"><img src="https://badgen.net/pypi/v/ckernel"></a>
</p>

This package provides a Jupyter kernel which allows automatic compilation and
execution of C/C++ code from a notebook environment.

Documentation:

- [Installation](https://c-kernel.readthedocs.io/en/latest/00-install.html)
- [Using c-kernel](https://c-kernel.readthedocs.io/en/latest/01-use.html)
- [Examples](https://c-kernel.readthedocs.io/en/latest/02-example.html)
- [FAQs](https://c-kernel.readthedocs.io/en/latest/03-FAQ.html)

## Features

Using c-kernel, you can:

- Automatically compile and execute code cells

<p align="center">
<img src="docs/img/demo-basic.png">
</p>

- Add compiler options using `//%` magic comments

<p align="center">
<img src="docs/img/demo-options.png">
</p>

- Compose multi-file programs in a single notebook

<p align="center">
<img src="docs/img/demo-multi-file.png">
</p>

- Get user input interactively

<p align="center">
<img src="docs/img/demo-interactive-input.png">
</p>


## Contact

For any issues, comments or feature requests, please go to the [issues page](https://github.com/adamtuft/c-kernel/issues).

## License and Copyright

Copyright (c) 2023, Adam Tuft

c-kernel is released under the BSD 3-clause license. See [LICENSE](<https://github.com/adamtuft/c-kernel/blob/main/LICENSE>) for details.
