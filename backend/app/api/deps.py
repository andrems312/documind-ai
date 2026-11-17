"""Dependências do FastAPI: sessão de banco, usuário autenticado e perfil."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.ai.rag import RagService
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.security import AuthUser, JWTVerifier
from app.db.models import Profile
from app.processing.jobs import JobRunner
from app.services.profiles import ensure_profile
from app.storage.base import StorageBackend

_bearer = HTTPBearer(auto_error=False, description="Token de acesso do Supabase Auth")


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Autenticação necessária.")
    verifier: JWTVerifier = request.app.state.jwt_verifier
    # A verificação pode buscar o JWKS pela rede na primeira chamada; não bloquear o event loop.
    user = await run_in_threadpool(verifier.user_from_token, credentials.credentials)
    request.state.user_id = str(user.id)
    return user


async def get_current_profile(
    user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profile:
    return await ensure_profile(db, user)


def get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage  # type: ignore[no-any-return]


def get_job_runner(request: Request) -> JobRunner:
    return request.app.state.job_runner  # type: ignore[no-any-return]


def get_rag(request: Request) -> RagService:
    return request.app.state.rag  # type: ignore[no-any-return]


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
CurrentProfile = Annotated[Profile, Depends(get_current_profile)]
StorageDep = Annotated[StorageBackend, Depends(get_storage)]
JobRunnerDep = Annotated[JobRunner, Depends(get_job_runner)]
RagDep = Annotated[RagService, Depends(get_rag)]
