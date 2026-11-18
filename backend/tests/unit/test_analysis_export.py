from __future__ import annotations

from datetime import UTC, datetime

from app.services import analysis_export as export

CREATED = datetime(2026, 11, 18, 10, 30, tzinfo=UTC)
CONTENT = (
    "# Visão geral\n\nEste é um **resumo** com *ênfase*.\n\n"
    "- Primeiro ponto\n- Segundo ponto\n\n## Detalhe\n\nTexto final."
)


def test_to_markdown_has_header_and_content() -> None:
    md = export.to_markdown(
        title="Resumo: Contrato",
        analysis_type="summary",
        titles=["Contrato A"],
        content=CONTENT,
        created_at=CREATED,
    )
    assert md.startswith("# Resumo: Contrato")
    assert "**Tipo:** Resumo" in md
    assert "Contrato A" in md
    assert "18/11/2026" in md
    assert CONTENT in md


def test_markdown_to_html_converts_subset() -> None:
    html = export.markdown_to_html("# Título\n\n- item um\n- item dois\n\nParágrafo **forte**.")
    assert "<h1>Título</h1>" in html
    assert html.count("<li>") == 2
    assert "<ul>" in html and "</ul>" in html
    assert "<b>forte</b>" in html


def test_markdown_to_html_escapes_html() -> None:
    html = export.markdown_to_html("Texto com <script>alert(1)</script> e & símbolo")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_to_pdf_produces_valid_pdf_bytes() -> None:
    pdf = export.to_pdf(
        title="Comparação: A × B",
        analysis_type="comparison",
        titles=["A", "B"],
        content=CONTENT,
        created_at=CREATED,
    )
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 500
