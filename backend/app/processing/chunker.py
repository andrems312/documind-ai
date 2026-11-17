"""Divisão do texto em chunks por contagem de tokens, sem cruzar páginas.

Estratégia:
- Unidades naturais: parágrafos; parágrafos longos viram frases; frases enormes são cortadas
  por janela de tokens.
- Unidades são agrupadas até `max_tokens`; o chunk seguinte começa repetindo as últimas unidades
  do anterior até `overlap_tokens`, preservando contexto nas fronteiras.
- Cada chunk pertence a uma única página, o que mantém a citação de página exata.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

import tiktoken

from app.processing.extractor import PageText

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=[A-ZÀ-Ý0-9\"'(“])")


@dataclass(frozen=True, slots=True)
class Chunk:
    page_number: int
    chunk_index: int
    content: str
    token_count: int


@dataclass(frozen=True, slots=True)
class _Unit:
    text: str
    tokens: int
    starts_paragraph: bool


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))


def _split_by_tokens(text: str, max_tokens: int) -> list[str]:
    tokens = _encoding().encode(text, disallowed_special=())
    return [
        _encoding().decode(tokens[i : i + max_tokens]).strip()
        for i in range(0, len(tokens), max_tokens)
    ]


def _hard_split(text: str, max_tokens: int) -> list[str]:
    """Corta texto sem pontuação útil em pedaços de até `max_tokens`, por fronteira de palavra."""
    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for word in text.split():
        n = count_tokens(" " + word)
        if n > max_tokens:  # "palavra" gigante (ex.: base64): só resta cortar por tokens
            if current:
                pieces.append(" ".join(current))
                current, current_tokens = [], 0
            pieces.extend(_split_by_tokens(word, max_tokens))
            continue
        if current and current_tokens + n > max_tokens:
            pieces.append(" ".join(current))
            current, current_tokens = [], 0
        current.append(word)
        current_tokens += n
    if current:
        pieces.append(" ".join(current))
    return [p for p in pieces if p]


def _units(text: str, max_tokens: int) -> Iterable[_Unit]:
    for paragraph in (p.strip() for p in text.split("\n\n")):
        if not paragraph:
            continue
        n = count_tokens(paragraph)
        if n <= max_tokens:
            yield _Unit(paragraph, n, True)
            continue
        first = True
        for sentence in _SENTENCE_SPLIT.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            pieces = (
                [sentence]
                if count_tokens(sentence) <= max_tokens
                else _hard_split(sentence, max_tokens)
            )
            for piece in pieces:
                if piece:
                    yield _Unit(piece, count_tokens(piece), first)
                    first = False


def _join(units: list[_Unit]) -> str:
    parts: list[str] = []
    for i, unit in enumerate(units):
        if i > 0:
            parts.append("\n\n" if unit.starts_paragraph else " ")
        parts.append(unit.text)
    return "".join(parts)


def _overlap_tail(units: list[_Unit], overlap_tokens: int) -> list[_Unit]:
    tail: list[_Unit] = []
    total = 0
    for unit in reversed(units):
        if total + unit.tokens > overlap_tokens:
            break
        tail.insert(0, unit)
        total += unit.tokens
    return tail


def chunk_pages(
    pages: Iterable[PageText], *, max_tokens: int = 500, overlap_tokens: int = 75
) -> list[Chunk]:
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens deve ser menor que max_tokens")

    chunks: list[Chunk] = []

    def emit(page_number: int, units: list[_Unit]) -> None:
        content = _join(units).strip()
        if content:
            chunks.append(Chunk(page_number, len(chunks), content, count_tokens(content)))

    for page in pages:
        current: list[_Unit] = []
        current_tokens = 0
        for unit in _units(page.text, max_tokens):
            if current and current_tokens + unit.tokens > max_tokens:
                emit(page.page_number, current)
                current = _overlap_tail(current, overlap_tokens)
                current_tokens = sum(u.tokens for u in current)
                while current and current_tokens + unit.tokens > max_tokens:
                    current_tokens -= current.pop(0).tokens
            current.append(unit)
            current_tokens += unit.tokens
        if current:
            emit(page.page_number, current)

    return chunks
