"""Configuração central da aplicação, carregada de variáveis de ambiente.

Ordem de precedência: variáveis do processo > `backend/.env` > `../.env` (raiz do monorepo).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Aplicação
    app_name: str = "DocuMind AI"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    # NoDecode: aceita "http://a.com,http://b.com" (formato do .env.example) em vez de exigir JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Banco de dados
    database_url: PostgresDsn

    # Supabase
    supabase_url: AnyHttpUrl
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_storage_bucket: str = "documents"
    jwt_audience: str = "authenticated"

    # Armazenamento de arquivos: "supabase" (produção) ou "local" (disco, dev/testes)
    storage_backend: Literal["supabase", "local"] = "local"
    local_storage_dir: str = str(BACKEND_DIR / ".uploads")

    # OpenRouter / IA
    openrouter_api_key: str = ""
    openrouter_base_url: AnyHttpUrl = AnyHttpUrl("https://openrouter.ai/api/v1")
    app_public_url: str = "http://localhost:3000"  # enviado ao OpenRouter como HTTP-Referer
    llm_model: str = "openai/gpt-4.1-mini"
    llm_temperature: float = Field(default=0.1, ge=0, le=1)
    llm_max_tokens: int = 1200
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 1536
    embedding_batch_size: int = Field(default=64, ge=1, le=256)
    http_timeout_seconds: float = 60.0

    # Chunking e recuperação (RAG)
    chunk_tokens: int = Field(default=500, ge=100, le=2000)
    chunk_overlap_tokens: int = Field(default=75, ge=0, le=500)
    rag_candidates: int = Field(default=20, ge=4, le=100)  # por estratégia (vetorial e full-text)
    rag_top_k: int = Field(default=8, ge=1, le=30)
    rag_min_similarity: float = Field(default=0.25, ge=0, le=1)
    rag_context_tokens: int = Field(default=6000, ge=500)
    rag_history_messages: int = Field(default=6, ge=0, le=30)

    # Processamento em segundo plano
    worker_concurrency: int = Field(default=2, ge=1, le=16)
    job_max_attempts: int = Field(default=3, ge=1, le=10)

    # Limites
    max_upload_mb: int = 25
    max_pdf_pages: int = 500

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        """URL do Postgres no formato do driver asyncpg (aceita o formato do Supabase)."""
        from app.db.session import to_asyncpg_url

        return to_asyncpg_url(str(self.database_url))

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def supabase_jwks_url(self) -> str:
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
