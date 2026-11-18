"""Exportação de análises para Markdown e PDF.

O conteúdo das análises já é Markdown. Para o PDF, convertemos um subconjunto de Markdown
(títulos, negrito, itálico, listas e parágrafos) para HTML e deixamos o PyMuPDF paginar.
"""

from __future__ import annotations

import html
import io
import re
from datetime import datetime

import pymupdf

_LABEL = {"summary": "Resumo", "key_info": "Informações-chave", "comparison": "Comparação"}
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _format_header(analysis_type: str, titles: list[str], created_at: datetime) -> str:
    label = _LABEL.get(analysis_type, analysis_type)
    docs = ", ".join(titles) if titles else "—"
    when = created_at.strftime("%d/%m/%Y %H:%M")
    return f"- **Tipo:** {label}\n- **Documentos:** {docs}\n- **Gerado em:** {when}"


def to_markdown(
    *, title: str, analysis_type: str, titles: list[str], content: str, created_at: datetime
) -> str:
    header = _format_header(analysis_type, titles, created_at)
    return f"# {title}\n\n{header}\n\n---\n\n{content}\n"


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = _BOLD.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC.sub(r"<i>\1</i>", escaped)
    return escaped


def markdown_to_html(markdown: str) -> str:
    """Converte um subconjunto de Markdown em HTML simples para o PyMuPDF renderizar."""
    lines = markdown.splitlines()
    parts: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if heading:
            close_list()
            level = min(len(heading.group(1)), 6)
            parts.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif bullet:
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{_inline(bullet.group(1))}</li>")
        else:
            close_list()
            parts.append(f"<p>{_inline(stripped)}</p>")
    close_list()
    return "\n".join(parts)


_PDF_CSS = """
body { font-family: sans-serif; color: #1a1f2b; }
h1 { font-size: 20px; margin: 0 0 6px; }
h2 { font-size: 15px; margin: 14px 0 4px; }
h3 { font-size: 13px; margin: 12px 0 4px; }
p, li { font-size: 10.5px; line-height: 1.5; margin: 0 0 6px; }
ul { margin: 0 0 6px 0; padding-left: 18px; }
hr { border: none; border-top: 1px solid #c9cedb; margin: 10px 0; }
"""


def to_pdf(
    *, title: str, analysis_type: str, titles: list[str], content: str, created_at: datetime
) -> bytes:
    markdown = to_markdown(
        title=title,
        analysis_type=analysis_type,
        titles=titles,
        content=content,
        created_at=created_at,
    )
    body_html = markdown_to_html(markdown)
    document = f"<html><body>{body_html}</body></html>"

    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    story = pymupdf.Story(html=document, user_css=_PDF_CSS)
    mediabox = pymupdf.paper_rect("a4")
    where = mediabox + (40, 40, -40, -40)
    more = True
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()
    return buffer.getvalue()
