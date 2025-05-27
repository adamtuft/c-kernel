c-kernel |version|
==================

.. toctree::
    :hidden:

    Installing c-kernel <00-install.rst>
    Using c-kernel <01-use.rst>
    Example <02-example.rst>
    FAQs <03-FAQ.rst>


This package provides a Jupyter kernel which allows automatic compilation and
execution of C/C++ code from a notebook environment.

Try c-kernel for yourself on binder:

.. image:: https://mybinder.org/badge_logo.svg
 :target: https://mybinder.org/v2/gh/adamtuft/ckernel-binder-demo/main?urlpath=%2Fdoc%2Ftree%2FIntroduction.ipynb

.. note::

    This documentation is currently under construction.

Features
^^^^^^^^

Using c-kernel, you can:

- Automatically compile and execute code cells

.. image:: img/demo-basic.png
  :alt: Automatically compile and execute code

- Add compiler options using `//%` magic comments

.. image:: img/demo-options.png
  :alt: Use magic comments

- Compose multi-file programs in a single notebook

.. image:: img/demo-multi-file.png
  :alt: Compose multi-file programs

- Get user input interactively

.. image:: img/demo-interactive-input.png
  :alt: Get interactive input

Contact
^^^^^^^

For any issues, comments or feature requests, please go to https://github.com/adamtuft/c-kernel/issues

License and Copyright
^^^^^^^^^^^^^^^^^^^^^

Copyright (c) 2023, Adam Tuft

c-kernel is released under the BSD 3-clause license. See the `license file <https://github.com/adamtuft/c-kernel/blob/main/LICENSE>`_ for details.
