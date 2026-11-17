"""Engine e fábrica de sessões assíncronas (SQLAlchemy 2 + asyncpg).

Compatível com o pooler do Supabase em modo transação (PgBouncer): o cache de prepared
statements do asyncpg é desativado e os nomes recebem UUIDs para evitar colisões.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def to_asyncpg_url(url: str) -> str:
    """Converte uma URL do Postgres (formato do Supabase) para o driver asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        to_asyncpg_url(database_url),
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
            "server_settings": {"application_name": "documind-api"},
        },
    )


SessionFactory = async_sessionmaker[AsyncSession]


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def session_scope(factory: SessionFactory) -> AsyncIterator[AsyncSession]:
    """Sessão fora do ciclo de requisição (jobs, streaming): commit no fim, rollback no erro."""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
