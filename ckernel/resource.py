import os

# importlib.resources available from 3.7
from importlib.resources import path, contents

import ckernel.resources

_all = {}
for name in contents(ckernel.resources):
    with path(ckernel.resources, name) as fullpath:
        _all[os.path.basename(fullpath)] = fullpath


def get(key: str, default=None):
    """Get the path to a resource by its name, or the default if not found"""
    return _all.get(key, default)


input_wrappers_src = _all["ck_input_wrappers.c"]
