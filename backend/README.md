# DocuMind AI — Backend

API FastAPI com pipeline RAG (PyMuPDF → chunks → embeddings → pgvector → OpenRouter).

## Executar

```bash
uv sync                      # instala dependências (cria .venv)
uv run alembic upgrade head  # aplica migrações no banco de DATABASE_URL
uv run uvicorn app.main:app --reload --port 8000
```

Documentação interativa: http://localhost:8000/docs

## Testes e qualidade

```bash
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```

Testes que exigem banco real rodam apenas com `TEST_DATABASE_URL` definida.

## Estrutura

- `app/core` — configuração, logs estruturados, segurança (JWT do Supabase), exceções, rate limit
- `app/api` — rotas versionadas (`/api/v1`) e dependências
- `app/db` — engine assíncrona, modelos SQLAlchemy e migrações Alembic
- `app/services` — regras de negócio
- `app/processing` — extração de PDF, chunking e jobs (FASE 3)
- `app/ai` — cliente OpenRouter, embeddings, recuperação híbrida e RAG (FASE 3)
- `app/storage` — adaptadores de armazenamento de arquivos (FASE 3)
