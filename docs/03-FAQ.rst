FAQs
====

.. contents:: FAQs
    :local:

1. Why does nothing happen when I request user input (e.g. with ``scanf``)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add ``#define _GNU_SOURCE`` before ``#include <stdio.h>``.

2. How do I get interactive input in C++?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Stick to functions in ``#include <cstdio>``. c-kernel doesn't support getting
input via ``std::cin`` through the notebook.

3. How do I send EOF (Ctrl+D) when waiting for user input?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Type ``^D`` into the input box.

4. Why am I seeing errors like "undefined reference to ``dlsym``"?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add ``-ldl`` to the ``--exe-ldflags`` option when installing the kernel, or add
the magic comment ``//% LDFLAGS -ldl`` to the code cell itself.
