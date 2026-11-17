"""Extração de texto por página com PyMuPDF, preservando o número da página.

Etapas:
1. Lê os blocos de texto de cada página em ordem de leitura (`sort=True`).
2. Normaliza Unicode (ligaduras, hífens condicionais) e junta palavras hifenizadas na quebra.
3. Remove cabeçalhos e rodapés repetidos (primeiro/último bloco repetido na maioria das páginas).
4. Detecta PDFs sem camada de texto (digitalizados) e falha com mensagem clara.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

import pymupdf

from app.core.exceptions import UnprocessableError

_MIN_TOTAL_CHARS = 50
_MIN_CHARS_PER_PAGE = 15
_HYPHEN_BREAK = re.compile(r"(\w)-\n(?=[a-zà-ÿ])")
_SPACES = re.compile(r"[ \t ]+")
_DIGITS = re.compile(r"\d+")


class ScannedPdfError(UnprocessableError):
    code = "pdf_without_text"


@dataclass(frozen=True, slots=True)
class PageText:
    page_number: int
    text: str


def _normalize_block(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("­", "").replace("\r", "")
    text = _HYPHEN_BREAK.sub(r"\1", text)
    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return " ".join(line for line in lines if line)


def _signature(block: str) -> str:
    """Forma canônica para comparar cabeçalhos/rodapés (ignora números de página)."""
    return _DIGITS.sub("#", block.lower())[:120]


def _page_blocks(page: pymupdf.Page) -> list[str]:
    blocks = page.get_text("blocks", sort=True)
    texts = (_normalize_block(b[4]) for b in blocks if b[6] == 0)
    return [t for t in texts if t]


def _strip_repeated_edges(pages: list[list[str]]) -> list[list[str]]:
    if len(pages) < 3:
        return pages
    threshold = max(2, int(len(pages) * 0.5))
    edge_counts: Counter[str] = Counter()
    for blocks in pages:
        edges = {_signature(b) for b in blocks[:1] + blocks[-1:]}
        edge_counts.update(edges)
    repeated = {sig for sig, count in edge_counts.items() if count >= threshold}
    if not repeated:
        return pages

    cleaned: list[list[str]] = []
    for blocks in pages:
        result = list(blocks)
        if result and _signature(result[0]) in repeated:
            result.pop(0)
        if result and _signature(result[-1]) in repeated:
            result.pop()
        cleaned.append(result)
    return cleaned


def extract_pages(data: bytes) -> list[PageText]:
    with pymupdf.open(stream=data, filetype="pdf") as document:
        pages = [_page_blocks(page) for page in document]

    pages = _strip_repeated_edges(pages)
    texts = ["\n\n".join(blocks) for blocks in pages]

    total_chars = sum(len(t) for t in texts)
    if total_chars < _MIN_TOTAL_CHARS or total_chars / max(len(texts), 1) < _MIN_CHARS_PER_PAGE:
        raise ScannedPdfError(
            "Não foi possível extrair texto deste PDF. Ele parece ser digitalizado (imagem) "
            "e o reconhecimento óptico (OCR) ainda não é suportado."
        )

    return [PageText(page_number=i + 1, text=text) for i, text in enumerate(texts)]
