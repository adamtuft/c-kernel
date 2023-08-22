import os
from pathlib import Path
from typing import Dict

# importlib.resources available from 3.7
import importlib.resources as pkg_resources

import ckernel.resources

_all: Dict[str, Path] = {}
for name in pkg_resources.contents(ckernel.resources):
    if pkg_resources.is_resource(ckernel.resources, name):
        with pkg_resources.path(ckernel.resources, name) as fullpath:
            _all[os.path.basename(fullpath)] = fullpath


def get(key: str, default=""):
    """Get the path to a resource by its name, or the default if not found"""
    return Path(_all.get(key, default))


input_wrappers_src = _all["ck_input_wrappers.c"]
