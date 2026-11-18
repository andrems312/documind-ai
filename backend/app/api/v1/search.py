from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentProfile, DbDep, EmbedderDep, SettingsDep
from app.core.rate_limit import limiter
from app.schemas.search import SearchResponse
from app.services import search as service

router = APIRouter()


@router.get(
    "",
    response_model=SearchResponse,
    summary="Busca semântica por significado em toda a biblioteca",
)
@limiter.limit("30/minute")
async def search_documents(
    request: Request,
    profile: CurrentProfile,
    db: DbDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    q: Annotated[str, Query(min_length=2, max_length=300)],
    folder_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    return await service.search(
        db,
        embedder,
        settings,
        user_id=profile.id,
        query=q,
        folder_id=folder_id,
        limit=limit,
    )
