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
