from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentProfile, DbDep
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services.profiles import update_profile

router = APIRouter()


@router.get("", response_model=ProfileRead, summary="Perfil do usuário autenticado")
async def read_me(profile: CurrentProfile) -> ProfileRead:
    return ProfileRead.model_validate(profile)


@router.patch("", response_model=ProfileRead, summary="Atualiza nome e avatar")
async def patch_me(payload: ProfileUpdate, profile: CurrentProfile, db: DbDep) -> ProfileRead:
    updated = await update_profile(db, profile, payload)
    return ProfileRead.model_validate(updated)
