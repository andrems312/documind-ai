"""Provedores de IA determinísticos para testes (nunca usados pela aplicação real).

- `HashingEmbedder`: bag-of-words com hashing → vetores normalizados; textos que compartilham
  palavras têm similaridade de cosseno alta, textos sem palavras em comum têm similaridade ~0.
- `ScriptedChat`: responde citando o trecho [1] do contexto e inclui de propósito uma citação
  inválida [9], para exercitar a validação de citações.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import AsyncIterator

from app.ai.providers import ChatCompletion, ChatMessage, ChatStreamEvent, EmbeddingBatch

_STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "é", "em", "no", "na", "nos",
    "nas", "um", "uma", "que", "qual", "quais", "com", "por", "para", "sobre", "como", "este",
    "esta", "deste", "desta", "ao", "aos", "se", "ser", "foi", "the",
}  # fmt: skip


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in normalized if not unicodedata.combining(c))


class HashingEmbedder:
    model = "fake/hashing-embedder"

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    def vector(self, text: str) -> list[float]:
        values = [0.0] * self.dim
        for word in re.findall(r"\w+", _fold(text)):
            if len(word) < 3 or word in _STOPWORDS:
                continue
            index = int(hashlib.md5(word.encode()).hexdigest(), 16) % (self.dim - 1) + 1
            values[index] += 1.0
        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0:
            values[0] = 1.0  # evita vetor nulo (cosseno indefinido)
            return values
        return [v / norm for v in values]

    async def embed(self, texts: list[str]) -> EmbeddingBatch:
        self.calls.append(list(texts))
        return EmbeddingBatch(
            vectors=[self.vector(t) for t in texts],
            prompt_tokens=sum(len(t.split()) for t in texts),
        )


class ScriptedChat:
    model = "fake/scripted-chat"

    def __init__(self) -> None:
        self.stream_calls: list[list[ChatMessage]] = []
        self.complete_calls: list[list[ChatMessage]] = []

    async def complete(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> ChatCompletion:
        self.complete_calls.append(messages)
        last = messages[-1]["content"].split("Última pergunta:")[-1].strip()
        return ChatCompletion(content=last, prompt_tokens=10, completion_tokens=5)

    async def stream(
        self, messages: list[ChatMessage], *, temperature: float, max_tokens: int
    ) -> AsyncIterator[ChatStreamEvent]:
        self.stream_calls.append(messages)
        context = messages[-1]["content"]
        match = re.search(r"\[1\] Documento: [^\n]*\n([^\n]+)", context)
        excerpt = match.group(1)[:160] if match else ""
        answer = f"De acordo com o documento: {excerpt} [1]. Um detalhe extra [9]."
        for piece in re.findall(r"\S+\s*", answer):
            yield ChatStreamEvent(delta=piece)
        yield ChatStreamEvent(prompt_tokens=120, completion_tokens=30)
