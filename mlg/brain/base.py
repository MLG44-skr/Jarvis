"""Wspólny interfejs mózgu, żeby dało się podmienić Ollamę na Claude bez ruszania bota."""

from typing import Protocol, TypedDict


class Message(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class BrainError(Exception):
    """Błąd, który da się pokazać szefowi w czacie."""


class Brain(Protocol):
    name: str

    async def chat(self, messages: list[Message]) -> str: ...

    async def close(self) -> None: ...
