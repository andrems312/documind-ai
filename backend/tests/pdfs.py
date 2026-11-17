"""Geração de PDFs reais (PyMuPDF) para os testes."""

from __future__ import annotations

import pymupdf

CONTRACT_PAGES = [
    (
        "CONTRATO DE PRESTAÇÃO DE SERVIÇOS\n\n"
        "Cláusula 1. As partes celebram o presente contrato de prestação de serviços de "
        "consultoria em tecnologia, nos termos e condições a seguir."
    ),
    (
        "Cláusula 2. O prazo de vigência deste contrato é de 24 meses, contados a partir da "
        "data de assinatura, podendo ser renovado por acordo entre as partes.\n\n"
        "Cláusula 3. O valor mensal dos serviços é de R$ 12.500,00, pago até o quinto dia útil."
    ),
    (
        "Cláusula 4. A rescisão antecipada sem justa causa implica multa de 20% sobre o saldo "
        "remanescente do contrato.\n\n"
        "Cláusula 5. Fica eleito o foro da comarca de Curitiba para dirimir quaisquer dúvidas."
    ),
]


def make_pdf(
    pages: list[str],
    *,
    header: str | None = None,
    footer: str | None = None,
    password: str | None = None,
) -> bytes:
    document = pymupdf.open()
    for number, text in enumerate(pages, start=1):
        page = document.new_page(width=595, height=842)
        if header:
            page.insert_text((50, 40), header, fontsize=9)
        if text:
            overflow = page.insert_textbox(
                pymupdf.Rect(50, 70, 545, 780), text, fontsize=11, fontname="helv"
            )
            assert overflow >= 0, "texto de teste não coube na página"
        if footer:
            page.insert_text((50, 815), footer.format(page=number), fontsize=9)
    options: dict[str, object] = {}
    if password:
        options = {
            "encryption": pymupdf.PDF_ENCRYPT_AES_256,
            "owner_pw": password,
            "user_pw": password,
        }
    data = document.tobytes(**options)
    document.close()
    return data


def contract_pdf() -> bytes:
    return make_pdf(
        CONTRACT_PAGES, header="ACME Consultoria Ltda.", footer="Página {page} de 3 - Confidencial"
    )
