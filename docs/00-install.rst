Installing c-kernel
===================

.. attention::
    C-kernel is officially supported on Linux and macOS, and on Windows using the Windows
    Subsystem for Linux (WSL). C-kernel *may* work on Windows without WSL (in which
    case you will need to install Microsoft Visual C++ 14.0 or greater), however this
    isn't officially supported.

.. contents: Contents

For the latest published version of c-kernel, install via pip:

:: 

    pip install ckernel


Alternatively, you can get the latest commits to c-kernel from Github:

:: 

    git clone -b dev https://github.com/adamtuft/c-kernel.git
    pip install ./c-kernel


To install the Jupyter kernel provided by c-kernel:

:: 

    python3 -m ckernel install ckernel "C/C++"

To use this kernel, select the kernel called "C/C++" when creating a new notebook.

Installation options
^^^^^^^^^^^^^^^^^^^^

When you install a kernel, you are installing a set of instructions which Jupyter
uses to launch the kernel (also known as a kernel specification). The specification
can be customised with options to the ``install`` command. See ``python3 -m ckernel install --help``
for a full listing of the options. Multiple specifications, each with a different
sets of options, can be installed by giving each a unique name and display name.

You can see a list of the installed kernel specifications with ``jupyter kernelspec list``.

.. attention::
    c-kernel requires a C/C++ compiler. By default it uses ``gcc`` and ``g++``,
    but you can change this with the ``--cc`` and ``--cxx`` options.

Positional arguments
--------------------

The ``install`` command has two positional arguments:

- ``name``: A name for this kernel specification. This is up to you, but must be unique among installed specifications.
- ``display-name``: The name for this kernel specification shown to users in Jupyter when selecting a kernel.


Optional arguments
------------------

-h, --help            show a help message and exit
--cc CC               the C compiler to use (default: gcc)
--cxx CXX             the C++ compiler to use (default: g++)
--exe-cflags CFLAGS   flags to pass to the C compiler when compiling/linking executables (default: None)
--exe-cxxflags CXXFLAGS
                    flags to pass to the C++ compiler when compiling/linking executables (default: None)
--exe-ldflags LDFLAGS
                    linker flags to pass when compiling/linking executables (default: None)
--user                install per-user only (default: False)
--prefix prefix       install under {prefix}/share/jupyter/kernels (default: None)
--debug               kernel reports debug messages to notebook user (default: False)
--startup script      a startup script to be sourced before launching the kernel (default: None)


Modifying the kernel's environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On some systems it may be necessary to control the environment within which the
kernel is launched. To do this, specify a startup script when installing the kernel
with the ``--startup`` argument. This script will then be sourced in the same
environment as the kernel, immediately before it is launched.

Inside a startup script, you can use the environment variables ``CKERNEL_NAME``
and ``CKERNEL_INSTALL_DIR`` to detect which kernel specification is being invoked.
These correspond to the ``name`` of the kernel specification and the location
where the specification was installed.

Starting the kernel in a virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the ``ckernel`` package was installed into a virtual environment ``ckernel-env``,
to activate it when the kernel is selected create a script which does just that:

.. code-block:: bash
    :caption: In ``~/start-ckernel-env.sh``:
    :linenos:

    #! /usr/bin/env bash
    source ~/.venv/ckernel-env/bin/activate

Then, set this as the startup script when installing the kernel specification:

::

    python3 -m ckernel install ckernel-with-env "C/C++ with env" --startup ~/start-ckernel-env.sh

The kernel will then be launched with the virtual environment active.



Using module files with the kernel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use module files to control the exact compiler used by the kernel, add a startup
script which loads the desired modules. For example:

.. code-block:: bash
    :caption: In ``~/load-gcc-12.2.sh``:
    :linenos:

    #! /usr/bin/env -S bash -l
    module load gcc/12.2

Then set this as the startup script for your kernel spec:

::

    python3 -m ckernel install ckernel-gcc122 "C/C++ (gcc 12.2)" --startup ~/load-gcc-12.2.sh
