from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentProfile, DbDep
from app.schemas.stats import StatsOverview
from app.services import stats as service

router = APIRouter()


@router.get("/overview", response_model=StatsOverview, summary="Métricas do dashboard")
async def stats_overview(profile: CurrentProfile, db: DbDep) -> StatsOverview:
    return await service.overview(db, profile.id)
