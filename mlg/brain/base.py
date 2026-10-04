"""Wspólny interfejs mózgu, żeby dało się podmienić Ollamę na Claude bez ruszania bota."""

from typing import Any, NotRequired, Protocol, TypedDict


class ToolCall(TypedDict):
    name: str
    arguments: dict[str, Any]


class Message(TypedDict):
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: NotRequired[list[dict]]
    tool_name: NotRequired[str]


class Reply(TypedDict):
    content: str
    tool_calls: list[ToolCall]
    raw: Message  # wiadomość asystenta w formacie mózgu, do odesłania w kolejnym kroku


class BrainError(Exception):
    """Błąd, który da się pokazać szefowi w czacie."""


class Brain(Protocol):
    name: str

    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> Reply: ...

    async def close(self) -> None: ...
