from app.core.config import Settings


def test_cors_origins_from_comma_separated_string(settings: Settings) -> None:
    custom = Settings(
        cors_origins="http://a.com, http://b.com",  # type: ignore[arg-type]
        database_url="postgresql://u:p@localhost:5432/db",
        supabase_url="https://x.supabase.co",
    )
    assert custom.cors_origins == ["http://a.com", "http://b.com"]


def test_database_url_is_converted_to_asyncpg(settings: Settings) -> None:
    assert settings.sqlalchemy_database_url.startswith("postgresql+asyncpg://")


def test_jwks_url_derived_from_supabase_url(settings: Settings) -> None:
    assert (
        settings.supabase_jwks_url
        == "https://test-project.supabase.co/auth/v1/.well-known/jwks.json"
    )


def test_max_upload_bytes(settings: Settings) -> None:
    assert settings.max_upload_bytes == settings.max_upload_mb * 1024 * 1024


def test_cors_origins_from_environment_variable(monkeypatch) -> None:
    """Formato do .env.example (lista separada por vírgula) precisa funcionar via ambiente."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,https://app.exemplo.com")
    assert Settings().cors_origins == ["http://localhost:3000", "https://app.exemplo.com"]  # type: ignore[call-arg]


def test_single_cors_origin_from_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    assert Settings().cors_origins == ["http://localhost:3000"]  # type: ignore[call-arg]


def test_env_example_file_is_parseable(monkeypatch) -> None:
    """O .env.example (com comentários na linha) precisa ser lido sem erro pelas Settings."""
    from app.core.config import ROOT_DIR

    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    parsed = Settings(  # type: ignore[call-arg]
        _env_file=ROOT_DIR / ".env.example",
        # os placeholders <ref>/<senha> do exemplo não são URLs válidas; o resto vem do arquivo
        database_url="postgresql://u:p@localhost:5432/db",
        supabase_url="https://x.supabase.co",
    )
    assert parsed.cors_origins == ["http://localhost:3000"]
    assert parsed.embedding_dim == 1536
    assert parsed.llm_model == "openai/gpt-4.1-mini"
