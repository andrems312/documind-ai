"""Proteções contra respostas sem fundamentação.

- Citações `[n]` que não correspondem a um trecho enviado ao modelo são removidas.
- Formatos alternativos (`[1, 2]`, `[1][3]`) são normalizados para `[1][2]`.
- A resposta padrão de ausência de informação é detectada para marcar a abstenção.
"""

from __future__ import annotations

import re
import unicodedata

NO_ANSWER = "Não encontrei essa informação nos documentos selecionados."

_CITATION_GROUP = re.compile(r"\[(\s*\d{1,3}(?:\s*[,;]\s*\d{1,3})*\s*)\]")
_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([.,;:!?])")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


def sanitize_citations(answer: str, n_sources: int) -> tuple[str, list[int]]:
    """Remove citações inválidas e devolve (texto, números citados em ordem de aparição)."""
    used: list[int] = []

    def replace(match: re.Match[str]) -> str:
        numbers = [int(n) for n in re.split(r"[,;]", match.group(1)) if n.strip()]
        valid = [n for n in numbers if 1 <= n <= n_sources]
        for n in valid:
            if n not in used:
                used.append(n)
        return "".join(f"[{n}]" for n in dict.fromkeys(valid))

    cleaned = _CITATION_GROUP.sub(replace, answer)
    cleaned = _SPACE_BEFORE_PUNCT.sub(r"\1", cleaned)
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    return cleaned.strip(), used


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in normalized if not unicodedata.combining(c))


def is_abstention(answer: str) -> bool:
    return _fold(NO_ANSWER).rstrip(".") in _fold(answer)
