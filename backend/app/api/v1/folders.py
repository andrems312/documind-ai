from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentProfile, DbDep
from app.schemas.folders import FolderCreate, FolderRead, FolderUpdate
from app.services import folders as service

router = APIRouter()


@router.post(
    "",
    response_model=FolderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma pasta",
)
async def create_folder(payload: FolderCreate, profile: CurrentProfile, db: DbDep) -> FolderRead:
    return await service.create_folder(db, profile.id, payload)


@router.get("", response_model=list[FolderRead], summary="Lista as pastas com contagem")
async def list_folders(profile: CurrentProfile, db: DbDep) -> list[FolderRead]:
    return await service.list_folders(db, profile.id)


@router.patch("/{folder_id}", response_model=FolderRead, summary="Renomeia ou recolore")
async def update_folder(
    folder_id: uuid.UUID, payload: FolderUpdate, profile: CurrentProfile, db: DbDep
) -> FolderRead:
    folder = await service.get_owned(db, profile.id, folder_id)
    return await service.update_folder(db, folder, payload)


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui a pasta (os documentos ficam sem pasta)",
)
async def delete_folder(folder_id: uuid.UUID, profile: CurrentProfile, db: DbDep) -> Response:
    folder = await service.get_owned(db, profile.id, folder_id)
    await service.delete_folder(db, folder)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
