"""Regras de negócio de pastas. Toda leitura/escrita filtra por `user_id` (posse)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import Document, Folder
from app.schemas.folders import FolderCreate, FolderRead, FolderUpdate


def _to_read(folder: Folder, document_count: int) -> FolderRead:
    return FolderRead(
        id=folder.id,
        name=folder.name,
        color=folder.color,
        document_count=document_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


async def _document_counts(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(Document.folder_id, func.count())
        .where(Document.user_id == user_id, Document.folder_id.is_not(None))
        .group_by(Document.folder_id)
    )
    return {folder_id: count for folder_id, count in rows if folder_id is not None}


async def list_folders(db: AsyncSession, user_id: uuid.UUID) -> list[FolderRead]:
    folders = (
        await db.scalars(select(Folder).where(Folder.user_id == user_id).order_by(Folder.name))
    ).all()
    counts = await _document_counts(db, user_id)
    return [_to_read(f, counts.get(f.id, 0)) for f in folders]


async def get_owned(db: AsyncSession, user_id: uuid.UUID, folder_id: uuid.UUID) -> Folder:
    folder = await db.scalar(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user_id)
    )
    if folder is None:
        raise NotFoundError("Pasta não encontrada.")
    return folder


async def _name_taken(
    db: AsyncSession, user_id: uuid.UUID, name: str, *, exclude: uuid.UUID | None = None
) -> bool:
    stmt = select(Folder.id).where(
        Folder.user_id == user_id, func.lower(Folder.name) == name.lower()
    )
    if exclude is not None:
        stmt = stmt.where(Folder.id != exclude)
    return await db.scalar(stmt) is not None


async def create_folder(db: AsyncSession, user_id: uuid.UUID, payload: FolderCreate) -> FolderRead:
    if await _name_taken(db, user_id, payload.name):
        raise ConflictError("Você já tem uma pasta com esse nome.")
    folder = Folder(user_id=user_id, name=payload.name, color=payload.color)
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return _to_read(folder, 0)


async def update_folder(db: AsyncSession, folder: Folder, payload: FolderUpdate) -> FolderRead:
    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None:
        if await _name_taken(db, folder.user_id, payload.name, exclude=folder.id):
            raise ConflictError("Você já tem uma pasta com esse nome.")
        folder.name = payload.name
    if "color" in fields:
        folder.color = payload.color
    await db.flush()
    await db.refresh(folder)
    counts = await _document_counts(db, folder.user_id)
    return _to_read(folder, counts.get(folder.id, 0))


async def delete_folder(db: AsyncSession, folder: Folder) -> None:
    # Os documentos da pasta têm folder_id com ON DELETE SET NULL: eles não são apagados.
    await db.delete(folder)
    await db.flush()
