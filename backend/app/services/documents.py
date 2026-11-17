"""Regras de negócio de documentos. Toda leitura/escrita filtra por `user_id` (posse)."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.models import Document, DocumentPage, DocumentStatus, JobStatus, ProcessingJob
from app.processing.validator import validate_pdf
from app.storage.base import StorageBackend, object_path

log = get_logger(__name__)


async def upload_document(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    data: bytes,
    storage: StorageBackend,
    settings: Settings,
) -> tuple[Document, ProcessingJob]:
    validated = await asyncio.to_thread(
        validate_pdf,
        filename,
        content_type,
        data,
        max_bytes=settings.max_upload_bytes,
        max_pages=settings.max_pdf_pages,
    )

    existing = await db.scalar(
        select(Document.id).where(Document.user_id == user_id, Document.sha256 == validated.sha256)
    )
    if existing:
        raise ConflictError("Você já enviou este arquivo.", details={"document_id": str(existing)})

    document_id = uuid.uuid4()
    path = object_path(user_id, document_id)
    await storage.put(path, data)

    document = Document(
        id=document_id,
        user_id=user_id,
        title=validated.title,
        original_filename=validated.original_filename,
        storage_path=path,
        file_size=validated.size,
        sha256=validated.sha256,
        page_count=validated.page_count,
        status=DocumentStatus.UPLOADED,
    )
    job = ProcessingJob(document_id=document_id)
    try:
        db.add(document)
        await db.flush()
        db.add(job)
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        await _safe_delete(storage, path)
        raise ConflictError("Você já enviou este arquivo.") from exc
    except Exception:
        await _safe_delete(storage, path)
        raise
    await db.refresh(document)
    return document, job


async def list_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: DocumentStatus | None = None,
    query: str | None = None,
) -> list[Document]:
    stmt = select(Document).where(Document.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Document.status == status)
    if query:
        stmt = stmt.where(Document.title.ilike(f"%{query.strip()}%"))
    return list((await db.scalars(stmt.order_by(Document.created_at.desc()))).all())


async def get_document(db: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    if document is None:
        # 404 (e não 403) para não revelar a existência de documentos de outros usuários.
        raise NotFoundError("Documento não encontrado.")
    return document


async def rename_document(db: AsyncSession, document: Document, title: str) -> Document:
    document.title = title.strip()
    await db.flush()
    await db.refresh(document)
    return document


async def delete_document(db: AsyncSession, document: Document, storage: StorageBackend) -> None:
    path = document.storage_path
    await db.delete(document)
    await db.flush()
    await _safe_delete(storage, path)


async def request_reprocess(db: AsyncSession, document: Document) -> ProcessingJob:
    active = await db.scalar(
        select(func.count())
        .select_from(ProcessingJob)
        .where(
            ProcessingJob.document_id == document.id,
            ProcessingJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
    )
    if active:
        raise ConflictError("O documento já está na fila de processamento.")
    document.status = DocumentStatus.UPLOADED
    document.error_message = None
    document.processed_pages = 0
    job = ProcessingJob(document_id=document.id)
    db.add(job)
    await db.flush()
    await db.refresh(document)
    return job


async def get_page(db: AsyncSession, document: Document, page_number: int) -> DocumentPage:
    page = await db.scalar(
        select(DocumentPage).where(
            DocumentPage.document_id == document.id, DocumentPage.page_number == page_number
        )
    )
    if page is None:
        raise NotFoundError("Página não encontrada ou documento ainda não processado.")
    return page


async def _safe_delete(storage: StorageBackend, path: str) -> None:
    try:
        await storage.delete(path)
    except Exception as exc:  # o registro já foi tratado; um arquivo órfão não deve quebrar a rota
        log.warning("storage_delete_failed", path=path, error=str(exc))
