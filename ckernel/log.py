"""Handle logging"""
from __future__ import annotations

from typing import Protocol, Any, Optional
from logging import Logger


class LoggingCallable(Protocol):
    def __call__(self, msg: str, *args: Any) -> None:
        ...


def log_info(log: Optional[Logger], prefix: str) -> LoggingCallable:
    "Define a function to send a prefixed info message"
    if log:

        def log_message(msg: str, *args) -> None:
            log.info("[%s] " + msg, prefix, *args)

        return log_message

    else:

        def do_nothing(msg: str, *args) -> None:  # pylint: disable=unused-argument
            pass

        return do_nothing
