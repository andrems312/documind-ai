"""Verifica a configuração do DocuMind AI contra os serviços REAIS, item por item.

Uso (na pasta backend):
    uv run python scripts/check_setup.py            # tudo, inclui 1 embedding e 1 chat mínimos
    uv run python scripts/check_setup.py --skip-ai  # sem chamadas pagas ao OpenRouter

Checa: variáveis do backend e do frontend, conexão com o Postgres, pgvector, migrações,
dimensão do vetor, Supabase Auth (URL, chave anon, validação de JWT), bucket do Storage
(privado + envio/leitura/exclusão de teste) e OpenRouter (chave, embeddings e chat).
Nenhum segredo é impresso. Sai com código 1 se algum item falhar.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import asyncpg  # noqa: E402
import httpx  # noqa: E402
from dotenv import dotenv_values  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.storage.supabase import supabase_server_headers  # noqa: E402

MARKERS = {"ok": "[ OK  ]", "warn": "[AVISO]", "fail": "[FALHA]", "skip": "[ --  ]"}


@dataclass
class Check:
    name: str
    status: str
    detail: str
    hint: str = ""


results: list[Check] = []


def report(name: str, status: str, detail: str, hint: str = "") -> None:
    check = Check(name, status, detail, hint)
    results.append(check)
    print(f"{MARKERS[status]} {name}: {detail}")
    if hint and status in {"fail", "warn"}:
        print(f"          -> {hint}")


# --------------------------------------------------------------------------- configuração
def load_settings() -> Settings | None:
    if not (ROOT_DIR / ".env").exists() and not (BACKEND_DIR / ".env").exists():
        report(
            "Arquivo .env",
            "fail",
            "não encontrado na raiz do projeto",
            "Copie .env.example para .env e preencha (veja supabase/README.md).",
        )
    try:
        settings = Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        fields = ", ".join(str(e["loc"][0]).upper() for e in exc.errors())
        report("Variáveis do backend", "fail", f"inválidas ou ausentes: {fields}")
        return None
    report("Variáveis do backend", "ok", f"carregadas (ambiente: {settings.app_env})")
    return settings


def check_frontend_env(settings: Settings) -> None:
    path = ROOT_DIR / "frontend" / ".env.local"
    if not path.exists():
        report(
            "Frontend .env.local",
            "fail",
            "não encontrado",
            "Copie frontend/.env.local.example para frontend/.env.local.",
        )
        return
    values = dotenv_values(path)
    problems: list[str] = []
    url = (values.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    if url != str(settings.supabase_url).rstrip("/"):
        problems.append("NEXT_PUBLIC_SUPABASE_URL difere de SUPABASE_URL")
    anon = values.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or ""
    if not anon:
        problems.append("NEXT_PUBLIC_SUPABASE_ANON_KEY vazia")
    elif settings.supabase_anon_key and anon != settings.supabase_anon_key:
        problems.append("NEXT_PUBLIC_SUPABASE_ANON_KEY difere de SUPABASE_ANON_KEY")
    if anon and anon == settings.supabase_service_role_key:
        problems.append("a chave do frontend é a SERVICE ROLE (nunca exponha essa chave!)")
    if not values.get("NEXT_PUBLIC_API_URL"):
        problems.append("NEXT_PUBLIC_API_URL vazia")
    if problems:
        report("Frontend .env.local", "fail", "; ".join(problems))
    else:
        report("Frontend .env.local", "ok", "coerente com o backend")


# --------------------------------------------------------------------------- banco
async def check_database(settings: Settings) -> None:
    url = str(settings.database_url).replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(url, timeout=15, statement_cache_size=0)
    except Exception as exc:  # noqa: BLE001
        report(
            "Postgres",
            "fail",
            f"não conectou ({type(exc).__name__}: {str(exc)[:120]})",
            "Confira DATABASE_URL (senha, host do pooler e porta 6543/5432).",
        )
        return
    try:
        version = await conn.fetchval("SHOW server_version")
        report("Postgres", "ok", f"conectado (versão {version})")

        available = await conn.fetchval(
            "SELECT default_version FROM pg_available_extensions WHERE name = 'vector'"
        )
        installed = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname='vector'"
        )
        if not available:
            report("pgvector", "fail", "extensão 'vector' indisponível neste servidor")
        elif installed:
            report("pgvector", "ok", f"instalada (versão {installed})")
        else:
            report("pgvector", "warn", "disponível, ainda não instalada", "Rode as migrações.")

        has_alembic = await conn.fetchval(
            "SELECT to_regclass('public.alembic_version') IS NOT NULL"
        )
        current = (
            await conn.fetchval("SELECT version_num FROM alembic_version") if has_alembic else None
        )
        head = _alembic_head()
        if current == head:
            report("Migrações", "ok", f"banco na versão {current} (head)")
        else:
            report(
                "Migrações",
                "fail",
                f"banco em {current or 'nenhuma'}, código em {head}",
                "Rode: uv run alembic upgrade head",
            )
            return

        column_type = await conn.fetchval(
            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
            "WHERE attrelid = 'public.document_chunks'::regclass AND attname = 'embedding'"
        )
        expected = f"vector({settings.embedding_dim})"
        if column_type == expected:
            report("Dimensão do vetor", "ok", f"{column_type} = EMBEDDING_DIM")
        else:
            report(
                "Dimensão do vetor",
                "fail",
                f"coluna é {column_type}, EMBEDDING_DIM={settings.embedding_dim}",
                "EMBEDDING_DIM mudou depois da migração: crie uma nova migração e reprocesse.",
            )
    finally:
        await conn.close()


def _alembic_head() -> str | None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini"))).get_current_head()


# --------------------------------------------------------------------------- supabase
async def check_supabase(settings: Settings, client: httpx.AsyncClient) -> None:
    base = str(settings.supabase_url).rstrip("/")
    anon = settings.supabase_anon_key
    if not anon:
        report("Supabase Auth", "warn", "SUPABASE_ANON_KEY vazia no backend; pulando teste")
    else:
        try:
            response = await client.get(f"{base}/auth/v1/settings", headers={"apikey": anon})
        except httpx.HTTPError as exc:
            report(
                "Supabase Auth",
                "fail",
                f"sem resposta ({type(exc).__name__})",
                "Confira SUPABASE_URL.",
            )
            return
        if response.status_code == 200:
            data = response.json()
            email = data.get("external", {}).get("email")
            confirm = "desativada" if data.get("mailer_autoconfirm") else "ativada"
            report(
                "Supabase Auth",
                "ok" if email else "fail",
                f"URL e chave anon válidas; login por e-mail {'ativo' if email else 'DESATIVADO'}; "
                f"confirmação de e-mail {confirm}",
                "" if email else "Ative Authentication > Providers > Email.",
            )
        else:
            report(
                "Supabase Auth",
                "fail",
                f"HTTP {response.status_code}",
                "Confira SUPABASE_URL e SUPABASE_ANON_KEY (Project Settings > API).",
            )

    if settings.supabase_jwt_secret:
        report("Validação de JWT", "ok", "via segredo HS256 (SUPABASE_JWT_SECRET)")
    else:
        try:
            jwks = (await client.get(settings.supabase_jwks_url)).json()
            keys = len(jwks.get("keys", []))
        except Exception:  # noqa: BLE001
            keys = 0
        if keys:
            report("Validação de JWT", "ok", f"via JWKS do projeto ({keys} chave(s) públicas)")
        else:
            report(
                "Validação de JWT",
                "fail",
                "JWKS vazio e SUPABASE_JWT_SECRET não definido",
                "Projeto usa segredo legado: copie o JWT Secret para SUPABASE_JWT_SECRET.",
            )


async def check_storage(settings: Settings, client: httpx.AsyncClient) -> None:
    if settings.storage_backend == "local":
        report(
            "Storage",
            "warn",
            f"modo local ({settings.local_storage_dir})",
            "Use 'supabase' em produção.",
        )
        return
    key = settings.supabase_service_role_key
    if not key:
        report(
            "Storage",
            "fail",
            "SUPABASE_SERVICE_ROLE_KEY vazia",
            "Necessária com STORAGE_BACKEND=supabase.",
        )
        return
    base = str(settings.supabase_url).rstrip("/")
    bucket = settings.supabase_storage_bucket
    response = await client.get(
        f"{base}/storage/v1/bucket/{bucket}",
        headers=supabase_server_headers(key),
    )
    if response.status_code in {400, 404} and "NoSuchBucket" in response.text:
        report(
            "Storage: bucket",
            "fail",
            f"a chave secreta funciona, mas o bucket '{bucket}' não existe",
            "Execute supabase/storage.sql no SQL Editor do Supabase.",
        )
        return
    if response.status_code != 200:
        report(
            "Storage: bucket",
            "fail",
            f"'{bucket}' inacessível (HTTP {response.status_code})",
            "Confira SUPABASE_SERVICE_ROLE_KEY (chave secret em Project Settings > API Keys).",
        )
        return
    if response.json().get("public"):
        report("Storage: bucket", "fail", f"'{bucket}' é PÚBLICO", "Torne o bucket privado.")
        return
    report("Storage: bucket", "ok", f"'{bucket}' existe e é privado")

    from app.storage.base import object_path
    from app.storage.supabase import SupabaseStorage

    storage = SupabaseStorage(base_url=base, service_role_key=key, bucket=bucket)
    path = object_path(uuid.uuid4(), uuid.uuid4())
    payload = b"%PDF-1.4\n% verificacao do DocuMind AI\n"
    try:
        await storage.put(path, payload)
        same = await storage.get(path) == payload
        await storage.delete(path)
        report("Storage: escrita", "ok" if same else "fail", "enviar, ler e excluir funcionam")
    except Exception as exc:  # noqa: BLE001
        report("Storage: escrita", "fail", str(exc)[:160])
    finally:
        await storage.aclose()


# --------------------------------------------------------------------------- openrouter
async def check_openrouter(settings: Settings, client: httpx.AsyncClient, skip_ai: bool) -> None:
    key = settings.openrouter_api_key
    if not key:
        report(
            "OpenRouter",
            "fail",
            "OPENROUTER_API_KEY vazia",
            "Crie uma chave em https://openrouter.ai/settings/keys.",
        )
        return
    base = str(settings.openrouter_base_url).rstrip("/")
    response = await client.get(f"{base}/key", headers={"Authorization": f"Bearer {key}"})
    if response.status_code != 200:
        report(
            "OpenRouter: chave",
            "fail",
            f"HTTP {response.status_code}",
            "Chave inválida ou revogada.",
        )
        return
    info = response.json().get("data", {})
    remaining = info.get("limit_remaining")
    detail = "chave válida" + (
        f"; limite restante US$ {remaining}" if remaining is not None else ""
    )
    report("OpenRouter: chave", "ok", detail)
    if skip_ai:
        report("OpenRouter: modelos", "skip", "pulado (--skip-ai)")
        return

    from app.ai.openrouter import OpenRouterClient

    ai = OpenRouterClient(
        api_key=key,
        base_url=base,
        chat_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        app_url=settings.app_public_url,
        max_retries=1,
    )
    try:
        try:
            batch = await ai.embed(["teste de conexão do DocuMind AI"])
            report(
                "OpenRouter: embeddings",
                "ok",
                f"{settings.embedding_model} gera vetores de {len(batch.vectors[0])} dimensões",
            )
        except Exception as exc:  # noqa: BLE001
            report("OpenRouter: embeddings", "fail", getattr(exc, "message", str(exc))[:200])
        try:
            reply = await ai.complete(
                [{"role": "user", "content": "Responda apenas: ok"}], temperature=0, max_tokens=5
            )
            report(
                "OpenRouter: chat",
                "ok",
                f"{settings.llm_model} respondeu ({reply.content.strip()[:20]!r})",
            )
        except Exception as exc:  # noqa: BLE001
            report("OpenRouter: chat", "fail", getattr(exc, "message", str(exc))[:200])
    finally:
        await ai.aclose()


# --------------------------------------------------------------------------- main
async def main(skip_ai: bool) -> int:
    print("DocuMind AI: verificação de configuração\n")
    settings = load_settings()
    if settings is None:
        return 1
    check_frontend_env(settings)
    await check_database(settings)
    async with httpx.AsyncClient(timeout=20) as client:
        await check_supabase(settings, client)
        await check_storage(settings, client)
        await check_openrouter(settings, client, skip_ai)

    failures = [r for r in results if r.status == "fail"]
    warnings = [r for r in results if r.status == "warn"]
    print(
        f"\nResumo: {len(results) - len(failures) - len(warnings)} ok, {len(warnings)} aviso(s), "
        f"{len(failures)} falha(s)."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--skip-ai", action="store_true", help="não chama modelos do OpenRouter")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.skip_ai)))
