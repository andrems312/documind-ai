# DocuMind AI

Plataforma SaaS para conversar com documentos PDF usando **RAG (Retrieval-Augmented Generation)**:
as respostas são geradas apenas a partir de trechos recuperados dos seus arquivos e vêm com a
página de origem citada.

[![CI](https://github.com/andrems312/documind-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/andrems312/documind-ai/actions/workflows/ci.yml)
[![Demo ao vivo](https://img.shields.io/badge/demo-ao%20vivo-7C6CF6?logo=vercel&logoColor=white)](https://documind-ai-five-pied.vercel.app)
![Next.js 15](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-HNSW-4169E1?logo=postgresql&logoColor=white)

### ▶ Demo ao vivo: **https://documind-ai-five-pied.vercel.app**

> Hospedado em plano gratuito — a **primeira** requisição após um período ocioso pode levar ~50s
> enquanto o backend "acorda" (cold start do Render). As seguintes são instantâneas.

**Destaques técnicos:** busca **híbrida** (vetorial pgvector + full-text em português, fundidas por
RRF) · respostas em **streaming** (SSE) com **citação de página** e abstenção quando não há base ·
pipeline de processamento **assíncrono e durável** · isolamento de usuários em **três camadas**
(aplicação + RLS + storage), com [revisão de segurança](SECURITY.md) documentada · **147 testes**
(backend + frontend) e CI que constrói as imagens Docker.

> Status: **FASE 5 (finalização) concluída** — suíte de testes ampliada, revisão de segurança
> documentada ([SECURITY.md](SECURITY.md)) e **deploy em produção** (Vercel + Render + Supabase),
> sobre as fases anteriores (fundação, núcleo RAG e experiência). Projeto entregue de ponta a ponta.
> Veja o roadmap completo em [docs/FASE1-PLANEJAMENTO.md](docs/FASE1-PLANEJAMENTO.md).

## Telas

| Dashboard | Documentos e pastas |
|---|---|
| ![Dashboard com estatísticas e gráfico de consumo](docs/screenshots/dashboard.jpg) | ![Biblioteca de documentos com pastas](docs/screenshots/documents.jpg) |

![Busca semântica com trechos ranqueados por afinidade](docs/screenshots/search.jpg)

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

## Deploy em produção

Arquitetura de deploy: **frontend na [Vercel](https://vercel.com)** (build nativo do Next),
**backend no [Render](https://render.com)** (imagem Docker) e **Supabase** para banco, auth e
storage. Render pode ser trocado por Fly.io ou Railway usando o mesmo `backend/Dockerfile`.

**1. Supabase** — crie o projeto e configure conforme [supabase/README.md](supabase/README.md):
chaves, bucket (`storage.sql`) e, em **Authentication → URL Configuration**, use a URL de produção
do frontend como *Site URL* e adicione `<url>/auth/callback` em *Redirect URLs*.

**2. Backend no Render** — "New +" → **Blueprint**, apontando para este repositório: o
[`render.yaml`](render.yaml) cria o serviço, aplica as migrações no *pre-deploy* e expõe o
health check. Defina no painel as variáveis marcadas como `sync: false` (`DATABASE_URL`,
chaves do Supabase, `OPENROUTER_API_KEY`, e `CORS_ORIGINS`/`APP_PUBLIC_URL` com a URL da Vercel).

**3. Frontend na Vercel** — importe o repositório com **Root Directory = `frontend`**. A Vercel
detecta o Next automaticamente. Defina as variáveis `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY` e `NEXT_PUBLIC_API_URL` (a URL pública do backend no Render).

**4. Ligar as pontas** — com a URL da Vercel conhecida, ajuste `CORS_ORIGINS` e `APP_PUBLIC_URL`
no Render e o *Site URL*/*Redirect URL* no Supabase. Faça um smoke test: cadastro → confirmação
por e-mail → login → upload de um PDF → pergunta no chat com citações.

> Dica: o CI (`.github/workflows/ci.yml`) já constrói as duas imagens Docker a cada push, então
> uma falha de build aparece antes do deploy.

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
