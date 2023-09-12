from __future__ import annotations

import asyncio
from typing import Coroutine, NoReturn, Protocol

from .trigger import AbstractTrigger


class StreamConsumer(Protocol):
    def __call__(self, reader: asyncio.StreamReader) -> Coroutine[None, None, None]:
        ...


class StreamWriter(Protocol):
    def __call__(
        self, writer: asyncio.StreamWriter, trigger: AbstractTrigger, prompt: str = ""
    ) -> NoReturn:
        ...
