from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Query, Request, Response, UploadFile, status

from app.api.deps import (
    CurrentProfile,
    DbDep,
    JobRunnerDep,
    SettingsDep,
    StorageDep,
)
from app.core.rate_limit import limiter
from app.db.models import DocumentStatus
from app.schemas.documents import DocumentPageRead, DocumentRead, DocumentUpdate
from app.services import documents as service

router = APIRouter()


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Envia um PDF e agenda o processamento",
)
@limiter.limit("30/minute")
async def upload_document(
    request: Request,
    profile: CurrentProfile,
    db: DbDep,
    storage: StorageDep,
    runner: JobRunnerDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="Arquivo PDF")],
) -> DocumentRead:
    # Lê no máximo limite+1 bytes: o validador rejeita o excesso sem carregar arquivos enormes.
    data = await file.read(settings.max_upload_bytes + 1)
    document, job = await service.upload_document(
        db,
        user_id=profile.id,
        filename=file.filename or "",
        content_type=file.content_type,
        data=data,
        storage=storage,
        settings=settings,
    )
    result = DocumentRead.model_validate(document)
    await db.commit()  # o job precisa estar visível antes de o worker começar
    runner.schedule(job.id)
    return result


@router.get("", response_model=list[DocumentRead], summary="Lista os documentos do usuário")
async def list_documents(
    profile: CurrentProfile,
    db: DbDep,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[DocumentRead]:
    documents = await service.list_documents(db, profile.id, status=status_filter, query=q)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead, summary="Detalhe e progresso")
async def get_document(document_id: uuid.UUID, profile: CurrentProfile, db: DbDep) -> DocumentRead:
    return DocumentRead.model_validate(await service.get_document(db, profile.id, document_id))


@router.patch("/{document_id}", response_model=DocumentRead, summary="Renomeia o documento")
async def update_document(
    document_id: uuid.UUID, payload: DocumentUpdate, profile: CurrentProfile, db: DbDep
) -> DocumentRead:
    document = await service.get_document(db, profile.id, document_id)
    return DocumentRead.model_validate(await service.rename_document(db, document, payload.title))


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui o documento, seus trechos e o arquivo",
)
async def delete_document(
    document_id: uuid.UUID, profile: CurrentProfile, db: DbDep, storage: StorageDep
) -> Response:
    document = await service.get_document(db, profile.id, document_id)
    await service.delete_document(db, document, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reexecuta extração, chunking e embeddings",
)
async def reprocess_document(
    document_id: uuid.UUID, profile: CurrentProfile, db: DbDep, runner: JobRunnerDep
) -> DocumentRead:
    document = await service.get_document(db, profile.id, document_id)
    job = await service.request_reprocess(db, document)
    result = DocumentRead.model_validate(document)
    await db.commit()
    runner.schedule(job.id)
    return result


@router.get(
    "/{document_id}/pages/{page_number}",
    response_model=DocumentPageRead,
    summary="Texto extraído de uma página",
)
async def get_page(
    document_id: uuid.UUID, page_number: int, profile: CurrentProfile, db: DbDep
) -> DocumentPageRead:
    document = await service.get_document(db, profile.id, document_id)
    page = await service.get_page(db, document, page_number)
    return DocumentPageRead(
        document_id=document.id,
        page_number=page.page_number,
        page_count=document.page_count or 0,
        text=page.text,
    )


@router.get(
    "/{document_id}/file",
    summary="Baixa o PDF original",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_file(
    document_id: uuid.UUID, profile: CurrentProfile, db: DbDep, storage: StorageDep
) -> Response:
    document = await service.get_document(db, profile.id, document_id)
    data = await storage.get(document.storage_path)
    filename = quote(document.original_filename)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
        },
    )
