import hashlib

import pytest

from app.core.exceptions import PayloadTooLargeError, UnprocessableError
from app.processing.validator import sanitize_filename, title_from_filename, validate_pdf
from tests.pdfs import make_pdf

MB = 1024 * 1024


def _validate(data: bytes, name: str = "contrato.pdf", ctype: str | None = "application/pdf"):
    return validate_pdf(name, ctype, data, max_bytes=5 * MB, max_pages=10)


def test_valid_pdf_returns_metadata() -> None:
    data = make_pdf(["Primeira página", "Segunda página"])
    result = _validate(data, name="Relatório_Anual 2025.pdf")
    assert result.page_count == 2
    assert result.size == len(data)
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert result.title == "Relatório Anual 2025"
    assert result.original_filename == "Relatório_Anual 2025.pdf"


@pytest.mark.parametrize(
    ("data", "name", "ctype", "message"),
    [
        (b"", "a.pdf", "application/pdf", "vazio"),
        (b"isto nao e um pdf" * 10, "a.pdf", "application/pdf", "não é um PDF"),
        (b"%PDF-1.7 lixo corrompido", "a.pdf", "application/pdf", "corrompido"),
        (b"%PDF-1.7", "a.docx", "application/pdf", ".pdf"),
        (b"%PDF-1.7", "a.pdf", "image/png", "Tipo de arquivo"),
    ],
)
def test_invalid_inputs_are_rejected(data: bytes, name: str, ctype: str, message: str) -> None:
    with pytest.raises(UnprocessableError, match=message):
        _validate(data, name=name, ctype=ctype)


def test_too_large_is_rejected() -> None:
    data = make_pdf(["x"])
    with pytest.raises(PayloadTooLargeError):
        validate_pdf("a.pdf", "application/pdf", data, max_bytes=len(data) - 1, max_pages=10)


def test_too_many_pages_is_rejected() -> None:
    data = make_pdf(["página"] * 3)
    with pytest.raises(UnprocessableError, match="limite é 2"):
        validate_pdf("a.pdf", "application/pdf", data, max_bytes=5 * MB, max_pages=2)


def test_password_protected_pdf_is_rejected() -> None:
    data = make_pdf(["segredo"], password="1234")
    with pytest.raises(UnprocessableError, match="senha"):
        _validate(data)


def test_sanitize_filename_strips_paths_and_control_chars() -> None:
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("C:\\Users\\x\\doc\x00.pdf") == "doc.pdf"
    assert sanitize_filename("") == "documento.pdf"
    long_name = "a" * 300 + ".pdf"
    assert len(sanitize_filename(long_name)) <= 255
    assert sanitize_filename(long_name).endswith(".pdf")


def test_title_from_filename() -> None:
    assert title_from_filename("meu__arquivo_final.pdf") == "meu arquivo final"
    assert title_from_filename(".pdf") == "Documento sem título"
