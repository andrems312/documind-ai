from __future__ import annotations

import re
import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import AnalysisDep, CurrentProfile, DbDep
from app.core.rate_limit import limiter
from app.db.models import AnalysisType
from app.schemas.analyses import AnalysisCreate, AnalysisListItem, AnalysisRead
from app.services import analyses as service
from app.services import analysis_export as export

router = APIRouter()


async def _generate(
    analysis_type: AnalysisType,
    payload: AnalysisCreate,
    profile: CurrentProfile,
    analysis: AnalysisDep,
) -> AnalysisRead:
    return await analysis.generate(
        user_id=profile.id, analysis_type=analysis_type, document_ids=payload.document_ids
    )


@router.post(
    "/summary",
    response_model=AnalysisRead,
    status_code=status.HTTP_201_CREATED,
    summary="Gera um resumo de um ou mais documentos",
)
@limiter.limit("20/minute")
async def create_summary(
    request: Request, payload: AnalysisCreate, profile: CurrentProfile, analysis: AnalysisDep
) -> AnalysisRead:
    return await _generate(AnalysisType.SUMMARY, payload, profile, analysis)


@router.post(
    "/key-info",
    response_model=AnalysisRead,
    status_code=status.HTTP_201_CREATED,
    summary="Extrai informações-chave de um ou mais documentos",
)
@limiter.limit("20/minute")
async def create_key_info(
    request: Request, payload: AnalysisCreate, profile: CurrentProfile, analysis: AnalysisDep
) -> AnalysisRead:
    return await _generate(AnalysisType.KEY_INFO, payload, profile, analysis)


@router.post(
    "/comparison",
    response_model=AnalysisRead,
    status_code=status.HTTP_201_CREATED,
    summary="Compara dois ou mais documentos",
)
@limiter.limit("20/minute")
async def create_comparison(
    request: Request, payload: AnalysisCreate, profile: CurrentProfile, analysis: AnalysisDep
) -> AnalysisRead:
    return await _generate(AnalysisType.COMPARISON, payload, profile, analysis)


@router.get("", response_model=list[AnalysisListItem], summary="Lista as análises salvas")
async def list_analyses(profile: CurrentProfile, db: DbDep) -> list[AnalysisListItem]:
    return await service.list_analyses(db, profile.id)


@router.get("/{analysis_id}", response_model=AnalysisRead, summary="Detalhe de uma análise")
async def get_analysis(analysis_id: uuid.UUID, profile: CurrentProfile, db: DbDep) -> AnalysisRead:
    return await service.get_detail(db, profile.id, analysis_id)


@router.delete(
    "/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui uma análise"
)
async def delete_analysis(analysis_id: uuid.UUID, profile: CurrentProfile, db: DbDep) -> Response:
    analysis = await service.get_owned(db, profile.id, analysis_id)
    await service.delete_analysis(db, analysis)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "analise"


@router.get(
    "/{analysis_id}/export",
    summary="Exporta a análise em Markdown ou PDF",
    response_class=Response,
)
async def export_analysis(
    analysis_id: uuid.UUID,
    profile: CurrentProfile,
    db: DbDep,
    fmt: Annotated[str, Query(alias="format", pattern="^(md|pdf)$")] = "md",
) -> Response:
    detail = await service.get_detail(db, profile.id, analysis_id)
    filename = _slug(detail.title)
    if fmt == "pdf":
        data = export.to_pdf(
            title=detail.title,
            analysis_type=detail.type.value,
            titles=detail.document_titles,
            content=detail.content,
            created_at=detail.created_at,
        )
        media_type, ext = "application/pdf", "pdf"
    else:
        data = export.to_markdown(
            title=detail.title,
            analysis_type=detail.type.value,
            titles=detail.document_titles,
            content=detail.content,
            created_at=detail.created_at,
        ).encode("utf-8")
        media_type, ext = "text/markdown; charset=utf-8", "md"
    disposition = f"attachment; filename*=UTF-8''{quote(f'{filename}.{ext}')}"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": disposition, "Cache-Control": "private, no-store"},
    )
