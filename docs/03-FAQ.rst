FAQs
====

.. contents:: FAQs
    :local:

1. What operating systems does c-kernel support?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linux, macOS and Windows using the Windows Subsystem for Linux (WSL). It *may*
work on Windows without WSL (in which case you will need to install Microsoft
Visual C++ 14.0 or greater), however this isn't officially supported.

2. Why does nothing happen when I request user input (e.g. with ``scanf``)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Try adding ``#define _GNU_SOURCE`` before ``#include <stdio.h>``.

3. How do I get interactive input in C++?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Stick to functions in ``#include <cstdio>``. c-kernel doesn't support getting
input via ``std::cin`` through the notebook.

4. How do I send EOF (Ctrl+D) when waiting for user input?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Type ``^D`` into the input box.

5. Why am I seeing errors like "undefined reference to ``dlsym``"?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add ``-ldl`` to the ``--exe-ldflags`` option when installing the kernel, or add
the magic comment ``//% LDFLAGS -ldl`` to the code cell itself.
