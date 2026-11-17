"""Pipeline de ingestão: PDF → texto por página → chunks → embeddings → pgvector.

Cada etapa grava progresso no banco (`processed_pages`) para o frontend acompanhar. O pipeline é
idempotente: reprocessar apaga páginas e chunks anteriores do documento antes de recomeçar.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from itertools import batched

from sqlalchemy import delete, func, update

from app.ai.providers import EmbeddingProvider
from app.core.config import Settings
from app.core.logging import get_logger
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentStatus,
    UsageEvent,
    UsageKind,
)
from app.db.session import SessionFactory, session_scope
from app.processing.chunker import chunk_pages
from app.processing.extractor import extract_pages
from app.storage.base import StorageBackend

log = get_logger(__name__)


class DocumentGone(Exception):
    """O documento foi excluído durante o processamento."""


@dataclass(frozen=True, slots=True)
class PipelineContext:
    session_factory: SessionFactory
    storage: StorageBackend
    embedder: EmbeddingProvider
    settings: Settings


async def process_document(ctx: PipelineContext, document_id: uuid.UUID) -> None:
    settings = ctx.settings

    async with session_scope(ctx.session_factory) as db:
        document = await db.get(Document, document_id)
        if document is None:
            raise DocumentGone(str(document_id))
        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        document.processed_pages = 0
        document.processed_at = None
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        await db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        storage_path, user_id = document.storage_path, document.user_id

    data = await ctx.storage.get(storage_path)
    pages = await asyncio.to_thread(extract_pages, data)
    chunks = await asyncio.to_thread(
        chunk_pages,
        pages,
        max_tokens=settings.chunk_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    log.info(
        "document_extracted", document_id=str(document_id), pages=len(pages), chunks=len(chunks)
    )

    async with session_scope(ctx.session_factory) as db:
        db.add_all(
            DocumentPage(
                document_id=document_id,
                page_number=page.page_number,
                text=page.text,
                char_count=len(page.text),
            )
            for page in pages
        )
        await db.execute(
            update(Document).where(Document.id == document_id).values(page_count=len(pages))
        )

    embedding_tokens = 0
    for batch in batched(chunks, settings.embedding_batch_size):
        result = await ctx.embedder.embed([chunk.content for chunk in batch])
        embedding_tokens += result.prompt_tokens
        async with session_scope(ctx.session_factory) as db:
            db.add_all(
                DocumentChunk(
                    document_id=document_id,
                    user_id=user_id,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    embedding=vector,
                    metadata_={"chars": len(chunk.content)},
                )
                for chunk, vector in zip(batch, result.vectors, strict=True)
            )
            # Progresso por página: tudo até a página do último chunk do lote está indexado.
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(processed_pages=batch[-1].page_number)
            )

    async with session_scope(ctx.session_factory) as db:
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status=DocumentStatus.READY,
                processed_pages=len(pages),
                processed_at=func.now(),
            )
        )
        db.add(
            UsageEvent(
                user_id=user_id,
                kind=UsageKind.UPLOAD,
                document_id=document_id,
                prompt_tokens=embedding_tokens,
            )
        )
    log.info("document_ready", document_id=str(document_id), embedding_tokens=embedding_tokens)
