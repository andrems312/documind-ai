"""Perfis: criados/atualizados preguiçosamente a partir do JWT verificado do Supabase."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthUser
from app.db.models import Profile
from app.schemas.profile import ProfileUpdate


async def ensure_profile(db: AsyncSession, user: AuthUser) -> Profile:
    """Garante que exista um perfil para o usuário autenticado.

    Caminho comum (perfil existente) é só leitura; a inserção é idempotente e segura contra
    requisições concorrentes do mesmo usuário (ON CONFLICT DO NOTHING).
    """
    profile = await db.scalar(select(Profile).where(Profile.id == user.id))
    if profile is None:
        await db.execute(
            insert(Profile)
            .values(
                id=user.id, email=user.email, full_name=user.full_name, avatar_url=user.avatar_url
            )
            .on_conflict_do_nothing(index_elements=[Profile.id])
        )
        profile = await db.scalar(select(Profile).where(Profile.id == user.id))
        assert profile is not None
    elif user.email and profile.email != user.email:
        profile.email = user.email
        await db.flush()
    return profile


async def get_profile(db: AsyncSession, user: AuthUser) -> Profile | None:
    return await db.scalar(select(Profile).where(Profile.id == user.id))


async def update_profile(db: AsyncSession, profile: Profile, payload: ProfileUpdate) -> Profile:
    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data:
        profile.full_name = data["full_name"]
    if "avatar_url" in data:
        profile.avatar_url = str(data["avatar_url"]) if data["avatar_url"] else None
    await db.flush()
    return profile
