"""Ambiente do Alembic (modo assíncrono, asyncpg).

A URL vem de `DATABASE_URL` (via Settings). Testes podem sobrescrevê-la com
`config.set_main_option("sqlalchemy.url", ...)`.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import *  # noqa: F401,F403 — registra todos os modelos no metadata
from app.db.session import create_engine, to_asyncpg_url

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
database_url = to_asyncpg_url(
    config.get_main_option("sqlalchemy.url") or get_settings().sqlalchemy_database_url
)


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_engine(database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
