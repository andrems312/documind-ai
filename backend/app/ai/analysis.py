"""Geração de análises (resumo, extração de informações, comparação) sobre documentos.

Fluxo:
1. Carrega os documentos (posse + status READY) e monta o texto dentro de um orçamento de tokens.
2. Monta o prompt do tipo pedido e chama o LLM (sem streaming: o resultado é persistido).
3. Salva a análise e um evento de uso; devolve o registro pronto para o frontend.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import (
    COMPARISON_PROMPT,
    KEY_INFO_PROMPT,
    SUMMARY_PROMPT,
    build_analysis_messages,
)
from app.ai.providers import ChatProvider
from app.core.config import Settings
from app.core.exceptions import AppError, UnprocessableError
from app.core.logging import get_logger
from app.db.models import (
    Analysis,
    AnalysisType,
    Document,
    DocumentPage,
    DocumentStatus,
    UsageEvent,
    UsageKind,
)
from app.db.session import SessionFactory, session_scope
from app.processing.chunker import truncate_to_tokens
from app.schemas.analyses import AnalysisRead

log = get_logger(__name__)

_PROMPTS = {
    AnalysisType.SUMMARY: SUMMARY_PROMPT,
    AnalysisType.KEY_INFO: KEY_INFO_PROMPT,
    AnalysisType.COMPARISON: COMPARISON_PROMPT,
}
_USAGE_KIND = {
    AnalysisType.SUMMARY: UsageKind.SUMMARY,
    AnalysisType.KEY_INFO: UsageKind.KEY_INFO,
    AnalysisType.COMPARISON: UsageKind.COMPARISON,
}
_LABEL = {
    AnalysisType.SUMMARY: "Resumo",
    AnalysisType.KEY_INFO: "Informações-chave",
    AnalysisType.COMPARISON: "Comparação",
}


def _title(analysis_type: AnalysisType, titles: list[str]) -> str:
    if analysis_type == AnalysisType.COMPARISON:
        return f"Comparação: {' × '.join(titles)}"
    if len(titles) == 1:
        return f"{_LABEL[analysis_type]}: {titles[0]}"
    return f"{_LABEL[analysis_type]} de {len(titles)} documentos"


class AnalysisService:
    def __init__(
        self, *, settings: Settings, session_factory: SessionFactory, chat: ChatProvider
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.chat = chat

    async def generate(
        self,
        *,
        user_id: uuid.UUID,
        analysis_type: AnalysisType,
        document_ids: list[uuid.UUID],
    ) -> AnalysisRead:
        if analysis_type == AnalysisType.COMPARISON and len(set(document_ids)) < 2:
            raise UnprocessableError("A comparação precisa de pelo menos dois documentos.")
        if len(set(document_ids)) > self.settings.analysis_max_documents:
            raise UnprocessableError(
                f"No máximo {self.settings.analysis_max_documents} documentos por análise."
            )

        ordered_ids = list(dict.fromkeys(document_ids))
        async with session_scope(self.session_factory) as db:
            docs = await self._load_documents(db, user_id, ordered_ids)
            contents, truncated = await self._gather_contents(db, docs)

        titles = [title for title, _ in contents]
        messages = build_analysis_messages(_PROMPTS[analysis_type], contents, truncated=truncated)
        try:
            completion = await self.chat.complete(
                messages,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.analysis_max_tokens,
            )
        except AppError:
            raise
        content = completion.content.strip()
        if not content:
            raise UnprocessableError("O modelo não retornou conteúdo. Tente novamente.")

        return await self._persist(
            user_id=user_id,
            analysis_type=analysis_type,
            document_ids=ordered_ids,
            titles=titles,
            content=content,
            usage=(completion.prompt_tokens, completion.completion_tokens),
        )

    async def _load_documents(
        self, db: AsyncSession, user_id: uuid.UUID, document_ids: list[uuid.UUID]
    ) -> list[Document]:
        rows = (
            await db.scalars(
                select(Document).where(Document.user_id == user_id, Document.id.in_(document_ids))
            )
        ).all()
        by_id = {d.id: d for d in rows}
        missing = [str(d) for d in document_ids if d not in by_id]
        if missing:
            raise UnprocessableError(
                "Um ou mais documentos não foram encontrados.", details={"document_ids": missing}
            )
        not_ready = [d.title for d in rows if d.status != DocumentStatus.READY]
        if not_ready:
            raise UnprocessableError(
                "Todos os documentos precisam estar prontos (processados).",
                details={"documents": not_ready},
            )
        # Preserva a ordem pedida pelo usuário (importante na comparação).
        return [by_id[d] for d in document_ids]

    async def _gather_contents(
        self, db: AsyncSession, docs: list[Document]
    ) -> tuple[list[tuple[str, str]], bool]:
        budget = max(500, self.settings.analysis_input_tokens // len(docs))
        contents: list[tuple[str, str]] = []
        truncated = False
        for doc in docs:
            pages = (
                await db.scalars(
                    select(DocumentPage.text)
                    .where(DocumentPage.document_id == doc.id)
                    .order_by(DocumentPage.page_number)
                )
            ).all()
            text, cut = truncate_to_tokens("\n\n".join(pages).strip(), budget)
            truncated = truncated or cut
            contents.append((doc.title, text))
        return contents, truncated

    async def _persist(
        self,
        *,
        user_id: uuid.UUID,
        analysis_type: AnalysisType,
        document_ids: list[uuid.UUID],
        titles: list[str],
        content: str,
        usage: tuple[int, int],
    ) -> AnalysisRead:
        async with session_scope(self.session_factory) as db:
            analysis = Analysis(
                user_id=user_id,
                type=analysis_type,
                document_ids=document_ids,
                title=_title(analysis_type, titles),
                content=content,
                model=self.chat.model,
            )
            db.add(analysis)
            db.add(
                UsageEvent(
                    user_id=user_id,
                    kind=_USAGE_KIND[analysis_type],
                    prompt_tokens=usage[0],
                    completion_tokens=usage[1],
                )
            )
            await db.flush()
            await db.refresh(analysis, attribute_names=["created_at"])
            log.info(
                "analysis_generated",
                analysis_id=str(analysis.id),
                type=analysis_type.value,
                documents=len(document_ids),
            )
            return AnalysisRead(
                id=analysis.id,
                type=analysis.type,
                document_ids=document_ids,
                document_titles=titles,
                title=analysis.title,
                content=analysis.content,
                model=analysis.model,
                created_at=analysis.created_at,
            )
