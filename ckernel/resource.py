from os import path

import ckernel.resources

try:
    import importlib.resources as resources
except ImportError:
    import importlib_resources as resources

_all = {
    path.basename(item): item
    for item in map(str, resources.files(ckernel.resources).iterdir())
}


def get(key: str, default=None):
    """Get the path to a resource by its name, or the default if not found"""
    return _all.get(key, default)


ckernel_mqueue_src = _all["ckernel_mqueue.c"]
ckernel_dyn_input_wrappers_src = _all["ckernel_dyn_input_wrappers.c"]
include_path = [_all["include"]]