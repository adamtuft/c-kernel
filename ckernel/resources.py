from os import path

from . import _resources

try:
    import importlib.resources as resources
except ImportError:
    import importlib_resources as resources

_all = {
    str(path.basename(str(item))): str(item)
    for item in resources.files(_resources).iterdir()
}

_top_level_files = {
    str(path.basename(str(item))): str(item)
    for item in resources.files(_resources).iterdir()
    if item.is_file()
}


def files():
    """Return a generator listing all top-level file names & paths"""
    return (pair for pair in _top_level_files.items())


def get(key: str, default=None):
    """Get the path to a resource by its name, or the default if not found"""
    return _all.get(key, default)


ckernel_mqueue_src = get("ckernel_mqueue.c")

include_path = [_all["include"]]
