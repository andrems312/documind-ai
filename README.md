# DocuMind AI

Plataforma SaaS para conversar com documentos PDF usando **RAG (Retrieval-Augmented Generation)**:
as respostas são geradas apenas a partir de trechos recuperados dos seus arquivos e vêm com a
página de origem citada.

> Status: **FASE 2 (Fundação) concluída** — autenticação, API, schema do banco e design system.
> Próxima: FASE 3 (upload, extração, embeddings, pgvector e chat com citações).
> Veja o roadmap completo em [docs/FASE1-PLANEJAMENTO.md](docs/FASE1-PLANEJAMENTO.md).

## Stack

| Camada | Tecnologias |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4, Lucide, TanStack Query |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, PyMuPDF |
| Dados | Supabase (Auth, Postgres 16 + pgvector, Storage) |
| IA | OpenRouter (chat e embeddings), pipeline RAG com busca híbrida |
| Infra | Docker, GitHub Actions, uv, pnpm |

## Estrutura

```
frontend/   Next.js + design system próprio
backend/    FastAPI + Alembic + serviços de IA
supabase/   Configuração do projeto Supabase (bucket e políticas)
docs/       Planejamento, arquitetura e ADRs
```

## Pré-requisitos

- Node.js 22+ e pnpm 10 (`npm i -g pnpm`)
- Python 3.12 e [uv](https://docs.astral.sh/uv/)
- Um projeto no [Supabase](https://supabase.com) (plano gratuito basta)
- Uma chave do [OpenRouter](https://openrouter.ai/settings/keys)

## Configuração

1. **Supabase**: siga [supabase/README.md](supabase/README.md) para criar o projeto, obter as chaves,
   configurar as URLs de redirecionamento e criar o bucket de arquivos.
2. **Backend**: copie `.env.example` para `.env` na raiz e preencha.
3. **Frontend**: copie `frontend/.env.local.example` para `frontend/.env.local` e preencha.

## Executar em desenvolvimento

```bash
# Terminal 1 — API (http://localhost:8000, docs em /docs)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — Web (http://localhost:3000)
cd frontend
pnpm install
pnpm dev
```

## Testes

```bash
cd backend && uv run pytest -q && uv run ruff check . && uv run mypy app
cd frontend && pnpm typecheck && pnpm test && pnpm build
```

## Docker (opcional)

`docker compose up --build` sobe Postgres com pgvector, a API (aplicando migrações) e o frontend.
A autenticação continua no Supabase; preencha o `.env` antes.

## Segurança

- Nenhuma chave secreta no frontend: só `NEXT_PUBLIC_SUPABASE_URL`, a chave **anon** (pública por
  design) e a URL da API.
- O backend valida o JWT do Supabase (HS256 ou JWKS) em toda rota e verifica a posse de cada recurso.
- RLS ativo em todas as tabelas como segunda camada; bucket de arquivos privado.
- Headers de segurança, CORS restrito, rate limit por usuário e logs estruturados com `request_id`.

## Documentação

- [docs/FASE1-PLANEJAMENTO.md](docs/FASE1-PLANEJAMENTO.md) — arquitetura, modelo de dados e roadmap
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — decisões de arquitetura (ADRs)
- `http://localhost:8000/docs` — OpenAPI gerado pelo FastAPI
