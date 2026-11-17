import pytest

from app.processing.extractor import ScannedPdfError, extract_pages
from tests.pdfs import CONTRACT_PAGES, contract_pdf, make_pdf


def test_extracts_text_per_page_with_page_numbers() -> None:
    pages = extract_pages(contract_pdf())
    assert [p.page_number for p in pages] == [1, 2, 3]
    assert "prazo de vigência" in pages[1].text
    assert "foro da comarca de Curitiba" in pages[2].text


def test_repeated_header_and_footer_are_removed() -> None:
    pages = extract_pages(contract_pdf())
    for page in pages:
        assert "ACME Consultoria" not in page.text
        assert "Confidencial" not in page.text


def test_paragraphs_are_preserved_and_lines_joined() -> None:
    page = extract_pages(contract_pdf())[1]
    assert "\n\n" in page.text  # parágrafos separados
    # quebras de linha dentro do parágrafo viram espaço
    assert "24 meses, contados a partir da data de assinatura" in page.text


def test_hyphenated_line_breaks_are_joined() -> None:
    data = make_pdf(
        ["A documenta-\nção completa do projeto está anexa ao processo administrativo."]
    )
    assert "documentação completa" in extract_pages(data)[0].text


def test_pdf_without_text_raises_clear_error() -> None:
    with pytest.raises(ScannedPdfError, match="OCR"):
        extract_pages(make_pdf(["", "", ""]))


def test_single_page_is_not_treated_as_header() -> None:
    pages = extract_pages(make_pdf([CONTRACT_PAGES[0]]))
    assert "CONTRATO DE PRESTAÇÃO DE SERVIÇOS" in pages[0].text
