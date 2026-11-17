"""Contratos dos provedores de IA usados pelo pipeline e pelo RAG.

O código de negócio depende destes protocolos, não do OpenRouter diretamente, o que permite
trocar de gateway e injetar implementações controladas nos testes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    prompt_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ChatCompletion:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    delta: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    extra: dict[str, object] = field(default_factory=dict)


class EmbeddingProvider(Protocol):
    model: str

    async def embed(self, texts: list[str]) -> EmbeddingBatch: ...


class ChatProvider(Protocol):
    model: str

    async def complete(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> ChatCompletion: ...

    def stream(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> AsyncIterator[ChatStreamEvent]: ...
