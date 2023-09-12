"""ckernel utilities"""
from __future__ import annotations

import os
import platform
import traceback
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from tempfile import mkdtemp
from typing import NamedTuple, Optional


is_macOS: bool = platform.system() == "Darwin"


def temporary_directory(prefix: Optional[str] = None):
    "Return a temporary directory"
    return Path(mkdtemp(prefix=prefix))


class EnvironmentVariables(NamedTuple):
    CKERNEL_DEBUG: Optional[str]
    CKERNEL_CC: Optional[str]
    CKERNEL_CXX: Optional[str]
    CKERNEL_EXE_CFLAGS: Optional[str]
    CKERNEL_EXE_CXXFLAGS: Optional[str]
    CKERNEL_EXE_LDFLAGS: Optional[str]


def get_environment_variables(default: Optional[str] = None) -> EnvironmentVariables:
    return EnvironmentVariables(
        **{name: os.getenv(name, default) for name in EnvironmentVariables._fields}
    )


@contextmanager
def switch_directory(new: str):
    old = os.getcwd()
    os.chdir(new)
    yield
    os.chdir(old)


class Stream(str, Enum):
    """Constants representing standard output channels"""

    STDERR = "stderr"
    STDOUT = "stdout"


STDERR = Stream.STDERR
STDOUT = Stream.STDOUT


class Lang(str, Enum):
    """Represents the recognised languages"""

    C = "C"
    CPP = "C++"


language = {
    "c": Lang.C,
    "cpp": Lang.CPP,
    "cxx": Lang.CPP,
    "cc": Lang.CPP,
}


def success(execution_count: int) -> dict[str, str | int]:
    """Construct a dict representing a success message"""
    return {"status": "ok", "execution_count": execution_count}


def error(
    ename: str, evalue: str, trace: Optional[list[str]] = None
) -> dict[str, str | list[str]]:
    """Construct a dict representing an error message"""
    return {
        "status": "error",
        "ename": ename,
        "evalue": evalue,
        "traceback": trace or [],
    }


def error_from_exception(exc_type, exc, tb):
    """Get the last traceback and return the message and an error dict"""
    tb_str = "\n".join(traceback.format_tb(tb))
    message = f"{tb_str}\n{exc_type.__name__}: {exc}"
    return message, error(exc_type.__name__, str(exc), traceback.format_tb(tb))
