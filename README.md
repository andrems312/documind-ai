# DocuMind AI

Plataforma SaaS para conversar com documentos PDF usando **RAG (Retrieval-Augmented Generation)**:
as respostas são geradas apenas a partir de trechos recuperados dos seus arquivos e vêm com a
página de origem citada.

> Status: **FASE 3 (núcleo) concluída** — upload, extração com PyMuPDF, chunking, embeddings,
> pgvector, busca híbrida, RAG com streaming e citações por página.
> Próxima: FASE 4 (dashboard de uso, pastas, resumos, comparação, busca semântica, exportação).
> Veja o roadmap completo em [docs/FASE1-PLANEJAMENTO.md](docs/FASE1-PLANEJAMENTO.md).

## Como funciona

```
PDF ─► validação (assinatura, senha, limites) ─► Storage privado
    ─► job em segundo plano: texto por página (PyMuPDF, sem cabeçalhos/rodapés repetidos)
    ─► chunks de ~500 tokens sem cruzar páginas ─► embeddings (OpenRouter) ─► pgvector (HNSW)

Pergunta ─► reescrita com o histórico ─► busca vetorial + full-text PT-BR ─► fusão RRF
        ─► sem trecho relevante? responde "não encontrei" sem chamar o LLM
        ─► contexto numerado ─► LLM em streaming (SSE) ─► validação das citações [n]
        ─► resposta + fontes (documento, página, trecho) salvas no histórico
```

Detalhes e decisões em [docs/ARQUITETURA.md](docs/ARQUITETURA.md); contrato da API e dos eventos
de streaming em [docs/API.md](docs/API.md).

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
4. **Verifique**: `cd backend && uv run alembic upgrade head && uv run python scripts/check_setup.py`
   testa cada serviço real e aponta exatamente o que corrigir.

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

Os testes de integração do backend (pgvector, pipeline, RAG, SSE, isolamento entre usuários) rodam
quando `TEST_DATABASE_URL` aponta para um Postgres com a extensão `vector`. **O schema do banco
indicado é apagado e recriado**; por segurança, os testes se recusam a rodar se o nome do banco
não contiver `test`:

```bash
# com Docker
docker run -d --name documind-test-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=documind_test -p 5433:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/documind_test uv run pytest -q
```

Sem Docker (inclusive no Windows), o pacote `pgserver` sobe um Postgres com pgvector embutido; veja
[docs/ARQUITETURA.md](docs/ARQUITETURA.md) (ADR-014).

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
