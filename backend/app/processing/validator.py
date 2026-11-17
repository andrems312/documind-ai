"""Validação de uploads de PDF.

Não confia em extensão nem em Content-Type: confere a assinatura `%PDF-`, abre o arquivo com o
PyMuPDF, rejeita PDFs protegidos por senha e aplica limites de tamanho e de páginas.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

import pymupdf

from app.core.exceptions import PayloadTooLargeError, UnprocessableError

_ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream", ""}
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class ValidatedPdf:
    original_filename: str
    title: str
    size: int
    sha256: str
    page_count: int


def sanitize_filename(filename: str) -> str:
    """Remove diretórios e caracteres de controle; limita o tamanho preservando a extensão."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = _CONTROL_CHARS.sub("", unicodedata.normalize("NFC", name)).strip().strip(".")
    if not name:
        name = "documento.pdf"
    if len(name) > 255:
        stem, _, ext = name.rpartition(".")
        name = f"{stem[: 250 - len(ext)]}.{ext}"
    return name


def title_from_filename(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    title = re.sub(r"[_\s]+", " ", stem).strip()
    return (title or "Documento sem título")[:255]


def validate_pdf(
    filename: str,
    content_type: str | None,
    data: bytes,
    *,
    max_bytes: int,
    max_pages: int,
) -> ValidatedPdf:
    safe_name = sanitize_filename(filename or "")
    if not safe_name.lower().endswith(".pdf"):
        raise UnprocessableError("Envie um arquivo com extensão .pdf.")
    if (content_type or "").split(";")[0].strip().lower() not in _ALLOWED_CONTENT_TYPES:
        raise UnprocessableError("Tipo de arquivo não suportado. Envie um PDF.")
    if not data:
        raise UnprocessableError("O arquivo está vazio.")
    if len(data) > max_bytes:
        raise PayloadTooLargeError(
            f"O arquivo excede o limite de {max_bytes // (1024 * 1024)} MB.",
            details={"max_bytes": max_bytes, "size": len(data)},
        )
    if b"%PDF-" not in data[:1024]:
        raise UnprocessableError("O arquivo não é um PDF válido.")

    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF lança tipos variados para arquivos corrompidos
        raise UnprocessableError(
            "Não foi possível abrir o PDF. O arquivo pode estar corrompido."
        ) from exc

    with document:
        if document.needs_pass:
            raise UnprocessableError("PDFs protegidos por senha não são suportados.")
        page_count = document.page_count

    if page_count == 0:
        raise UnprocessableError("O PDF não possui páginas.")
    if page_count > max_pages:
        raise UnprocessableError(
            f"O PDF tem {page_count} páginas; o limite é {max_pages}.",
            details={"page_count": page_count, "max_pages": max_pages},
        )

    return ValidatedPdf(
        original_filename=safe_name,
        title=title_from_filename(safe_name),
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
    )
