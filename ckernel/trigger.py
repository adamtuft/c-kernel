"""Implement AbstractTrigger"""
from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Optional
from contextlib import contextmanager
from logging import Logger

import sysv_ipc

from .log import log_info


class Trigger(ABC):
    """Block until a process signals that it is ready"""

    @abstractmethod
    def __init__(
        self,
        timeout: Optional[int] = None,
        logger: Optional[Logger] = None,
    ):
        ...

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the trigger is ready to be waited on"""

    @property
    @abstractmethod
    def env_key(self) -> str:
        """Returns the name of an environment variable used to store the name of the trigger"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns a name that can be used by other processes to identify the trigger"""

    @abstractmethod
    def wait(self):
        """Block until ready to trigger"""

    @abstractmethod
    def close(self, unlink: bool = True):
        """Close the trigger and clean up resources if asked"""

    @abstractmethod
    def ready(self, unlink: bool = True):
        """Make the trigger ready for waiting and call self.close() when done"""


class SysVSemTrigger(Trigger):
    """Block on a SystemV semaphore until a process signals that it is ready"""

    def __init__(
        self,
        timeout: Optional[int] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        self._sem: Optional[sysv_ipc.Semaphore] = None
        self.log_info = log_info(logger, self.__class__.__name__)
        self.log_info("created")
        self.timeout = timeout

    def __repr__(self) -> str:
        if self._sem is None:
            return f"{self.__class__.__name__}(key=None, id=None)"
        else:
            return f"{self.__class__.__name__}(key={self._sem.key}, id={self._sem.id})"

    @property
    def is_ready(self):
        return self._sem is not None

    @property
    def env_key(self) -> str:
        return "CK_SEMKEY"

    @property
    def name(self) -> str:
        return f"{self._sem.key}" if self._sem is not None else "None"

    def wait(self):
        self.log_info("%s wait", self.name)
        if self.is_ready:
            return self._sem.acquire(timeout=self.timeout)
        else:
            raise RuntimeError("can't wait on unready trigger")

    def close(self, unlink: bool = True):
        if self._sem is not None and unlink:
            self.log_info("%s stop", self.name)
            self._sem.remove()
            self._sem = None

    @contextmanager
    def ready(self, unlink: bool = True):
        # Note: sysv_ipc.Semaphore supports __enter__ and __exit__ but this only
        # acquires and releases the semaphore, it doesn't handle creation/removal
        self._sem = sysv_ipc.Semaphore(None, flags=sysv_ipc.IPC_CREX, initial_value=0)
        self.log_info("%s start", self.name)
        try:
            yield self
        finally:
            self.close(unlink=unlink)
