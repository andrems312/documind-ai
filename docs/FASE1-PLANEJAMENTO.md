# DocuMind AI — FASE 1: Planejamento

> Data: 16/11/2026 · Status: aguardando aprovação para iniciar a FASE 2

---

## 1. Análise do ambiente de desenvolvimento

| Item | Encontrado | Observação |
|---|---|---|
| Sistema operacional | Windows 11 Home 10.0.26300 | — |
| Hardware | Intel i5-1235U · 16 GB RAM · 255 GB livres | Suficiente para dev local sem GPU |
| Git | 2.54.0 | OK |
| Node.js / npm / pnpm | **não instalado** | Necessário para o frontend (Next.js) |
| Python | **não instalado** (só o atalho da Microsoft Store) | Necessário para o backend (FastAPI) |
| Docker Desktop | **não instalado** | Opcional (ver decisão abaixo) |
| PostgreSQL local / psql | **não instalado** | Não necessário: usaremos o Postgres do Supabase |
| Supabase CLI | **não instalado** | Opcional |
| Projeto DocuMind existente | nenhum | Partiremos do zero numa pasta nova |

### Pré-requisitos a instalar antes da FASE 2

```powershell
winget install OpenJS.NodeJS.LTS          # Node.js 22 LTS (inclui npm)
winget install Python.Python.3.12         # Python 3.12
winget install astral-sh.uv               # uv: gerenciador de deps Python (rápido, lockfile)
npm install -g pnpm                       # pnpm para o frontend
```

Docker Desktop é **opcional** no Windows: o banco (Postgres + pgvector), a autenticação e o
storage ficam no Supabase na nuvem desde o primeiro dia. O `docker-compose.yml` será entregue
para deploy e para quem quiser rodar tudo local, mas o fluxo de desenvolvimento principal
não depende dele.

### Contas e chaves necessárias (criadas pelo usuário, nunca inventadas)

| Serviço | O que obter | Onde |
|---|---|---|
| Supabase (projeto gratuito) | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL` (connection string) | Dashboard → Project Settings → API / Database |
| OpenRouter | `OPENROUTER_API_KEY` | openrouter.ai → Keys |

Limites relevantes do plano gratuito do Supabase (conferir em supabase.com/pricing):
500 MB de banco, 1 GB de storage, projeto pausa após 1 semana sem uso. Para um portfólio
isso basta; o schema será pensado para migrar para o plano Pro sem alterações.

---

## 2. Arquitetura proposta

### 2.1 Visão geral

```
┌────────────────────────────┐        ┌──────────────────────────────────────┐
│  Frontend · Next.js 15     │  HTTPS │  Backend · FastAPI (Python 3.12)     │
│  App Router · TS · Tailwind│ ─────► │  /api/v1  (REST + SSE para streaming) │
│  @supabase/ssr (auth)      │ Bearer │                                      │
└─────────────┬──────────────┘  JWT   │  ┌─────────────┐  ┌───────────────┐ │
              │ login/cadastro        │  │ Processing  │  │ AI / RAG      │ │
              ▼                       │  │ PyMuPDF     │  │ OpenRouter    │ │
┌────────────────────────────┐        │  │ chunking    │  │ embeddings    │ │
│  Supabase Auth             │ ◄──────│  │ jobs        │  │ retrieval     │ │
│  (JWT, e-mail, reset senha)│ verify │  └──────┬──────┘  └──────┬────────┘ │
└────────────────────────────┘        └─────────┼────────────────┼──────────┘
                                                ▼                ▼
                       ┌──────────────────────────────┐  ┌────────────────────┐
                       │ Supabase Postgres + pgvector  │  │ Supabase Storage   │
                       │ (dados, chunks, embeddings)   │  │ (PDFs, privado)    │
                       └──────────────────────────────┘  └────────────────────┘
```

### 2.2 Decisões de arquitetura (ADRs resumidas)

| # | Decisão | Alternativas consideradas | Motivo |
|---|---|---|---|
| ADR-001 | **Monorepo** com `frontend/`, `backend/`, `supabase/`, `docs/` | Dois repositórios | Um clone, um CI, documentação única; ideal para portfólio |
| ADR-002 | **Supabase Auth** no frontend; backend **só valida o JWT** (assinatura + expiração) e extrai `user_id` | Auth própria com FastAPI-Users | Cadastro, login, reset de senha e sessões seguras prontos e auditados; zero senha armazenada por nós |
| ADR-003 | Backend acessa o Postgres **diretamente** (SQLAlchemy 2 async + asyncpg) usando a connection string | PostgREST / supabase-py | Controle total do SQL vetorial (`<=>`, HNSW, busca híbrida); RLS mantido como segunda camada de defesa |
| ADR-004 | **Alembic** é a única fonte de verdade do schema, inclusive extensões, índices e políticas RLS | Migrations SQL do Supabase CLI | Versionamento junto do código do backend; reproduzível em qualquer Postgres com pgvector |
| ADR-005 | **Supabase Storage** (bucket privado) para PDFs, acesso via backend com URLs assinadas | Disco local / S3 | Sem servidor de arquivos próprio; adapter `StorageBackend` permite trocar por S3 ou disco |
| ADR-006 | **OpenRouter** para chat e embeddings (`/api/v1/chat/completions` e `/api/v1/embeddings`), via `httpx` com retry e timeout | SDK OpenAI apontando para o OpenRouter | Dependência mínima; os dois endpoints são compatíveis com o formato OpenAI |
| ADR-007 | Modelos **configuráveis por env** (`LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`) | Modelo fixo no código | Troca de modelo sem redeploy; dimensão do vetor validada na migração |
| ADR-008 | Processamento de PDF em **background dentro do próprio serviço** (tarefas asyncio + tabela `processing_jobs` durável) | Celery/arq + Redis desde o início | Sem Redis na infraestrutura mínima; a interface `JobRunner` permite plugar um worker externo (arq) na FASE 5 ou depois |
| ADR-009 | **Busca híbrida**: vetorial (cosine, HNSW) + full-text (`tsvector` em português) combinadas por RRF | Só vetorial | Termos exatos (nomes, números de cláusula, siglas) melhoram muito com full-text |
| ADR-010 | Resposta em **streaming (SSE)** com citações enviadas como evento final | Resposta completa | Experiência tipo ChatGPT; citações estruturadas, não "parseadas" do texto |
| ADR-011 | Isolamento por usuário em **três camadas**: filtro `user_id` em toda query, RLS no Postgres, políticas no bucket de storage | Só filtro na aplicação | Defesa em profundidade |
| ADR-012 | Logs estruturados JSON com `structlog`, `request_id` por requisição | logging padrão | Observabilidade pronta para a nuvem |

### 2.3 Stack definitiva

**Frontend** — Next.js 15 (App Router), React 19, TypeScript 5, Tailwind CSS 4, Lucide, `@supabase/ssr`,
TanStack Query (cache/estado servidor), Zustand (estado de UI), `react-hook-form` + `zod`, `sonner` (toasts),
`react-pdf` (visualização de páginas), Vitest + Testing Library, Playwright (e2e crítico).
Componentes próprios (botão, input, dialog, sheet, skeleton…) com identidade visual própria, sem template.

**Backend** — Python 3.12, FastAPI, Pydantic v2 + `pydantic-settings`, SQLAlchemy 2 (async) + asyncpg,
Alembic, `pgvector` (bindings), PyMuPDF, `tiktoken` (contagem de tokens para chunking), `httpx`,
`python-jose` (JWT), `structlog`, `slowapi` (rate limit), validação por assinatura de bytes,
pytest + pytest-asyncio + httpx `AsyncClient`, ruff + mypy.

**Dados/Infra** — Supabase (Auth, Postgres 16 + pgvector, Storage), Docker (Dockerfiles multi-stage +
compose com Postgres `pgvector/pgvector:pg16` para quem quiser rodar local), GitHub Actions (lint + testes).

### 2.4 Pipeline RAG (detalhado)

```
Upload ─► Validação ─► Storage ─► job "process_document"
                                        │
          ┌─────────────────────────────┘
          ▼
   1. PyMuPDF extrai texto por página (preserva page_number; detecta PDF escaneado/sem texto → status failed com motivo claro)
   2. Normalização (hifenização, espaços, cabeçalhos repetidos)
   3. Chunking por tokens: ~500 tokens, overlap 15%, nunca cruza página; metadados {document_id, page, chunk_index, section_hint}
   4. Embeddings em lotes (até 64 chunks/req) via OpenRouter, com retry exponencial
   5. INSERT em document_chunks (embedding vector(N) + tsvector gerado) · status → ready
```

```
Pergunta ─► 1. Reescrita contextual (usa últimas N mensagens para resolver "ele", "esse contrato")
            2. Embedding da pergunta
            3. Busca híbrida restrita aos documentos da conversa e ao user_id:
                 top-20 vetorial (cosine) ⊕ top-20 full-text PT-BR → RRF → top-8
            4. Filtro por score mínimo + dedupe por página + orçamento de tokens de contexto
            5. Prompt: system (regras PT-BR, só responder com base nos trechos, citar [n]) + trechos numerados + histórico + pergunta
            6. LLM via OpenRouter em streaming
            7. Se nenhum trecho passa no score mínimo, ou o modelo declara ausência → resposta padrão "não encontrado no documento"
            8. Persistência: message + message_citations (chunk, página, trecho, score)
```

Prevenção de alucinação: trechos numerados obrigatórios, instrução explícita de abstenção, score mínimo
antes de chamar o LLM, citações validadas contra os chunks realmente enviados (o modelo não pode citar
um [n] inexistente) e temperatura baixa.

Documentos grandes: extração página a página (streaming de memória), embeddings em lotes com progresso
(`processed_pages / page_count` exibido no frontend), limite configurável de páginas e tamanho (padrão 25 MB / 500 páginas).

### 2.5 Segurança

- Chaves só no backend (`.env`); o frontend recebe apenas `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`.
- Upload: extensão + MIME + assinatura `%PDF-`, tamanho máximo, limite de páginas, nome sanitizado, hash SHA-256 (dedupe por usuário).
- Toda rota autenticada; ownership verificado no serviço antes de qualquer leitura/escrita; 404 (não 403) para recursos de outros usuários.
- RLS ativo em todas as tabelas; bucket privado, download apenas via URL assinada de curta duração emitida pelo backend.
- Rate limit por usuário em rotas caras (upload, chat, resumo).
- CORS restrito à origem do frontend; headers de segurança; `.env.example` sem valores reais.

---

## 3. Estrutura de pastas

```
documind-ai/
├── README.md                     # visão geral, setup, screenshots
├── .env.example                  # todas as variáveis, sem valores
├── .gitignore
├── docker-compose.yml            # api + web + postgres(pgvector) para execução local/deploy
├── .github/workflows/ci.yml      # lint + testes (backend e frontend)
├── docs/
│   ├── FASE1-PLANEJAMENTO.md     # este documento
│   ├── ARQUITETURA.md            # diagrama + ADRs completas
│   ├── API.md                    # resumo dos endpoints (OpenAPI é gerado pelo FastAPI)
│   └── adr/                      # uma ADR por decisão
│
├── frontend/
│   ├── package.json · next.config.ts · tsconfig.json · Dockerfile
│   ├── public/
│   └── src/
│       ├── app/
│       │   ├── (marketing)/page.tsx                # landing simples
│       │   ├── (auth)/login | register | forgot-password | reset-password
│       │   ├── (app)/
│       │   │   ├── layout.tsx                      # sidebar + header + tema
│       │   │   ├── dashboard/
│       │   │   ├── documents/  [id]/               # lista, pastas, detalhe com páginas
│       │   │   ├── chat/       [conversationId]/
│       │   │   ├── compare/
│       │   │   ├── search/
│       │   │   └── settings/
│       │   └── auth/callback/route.ts              # troca de código do Supabase
│       ├── components/
│       │   ├── ui/            # botão, input, dialog, skeleton, badge, toast… (design system próprio)
│       │   ├── layout/        # sidebar, topbar, theme-toggle, empty-state
│       │   ├── documents/     # dropzone, card, status, folder-tree, page-viewer
│       │   ├── chat/          # message-list, composer, citation-chip, sources-panel
│       │   └── dashboard/     # stat-card, usage-chart
│       ├── lib/
│       │   ├── supabase/      # client.ts, server.ts, middleware.ts
│       │   ├── api/           # cliente HTTP tipado (fetch + token), sse.ts
│       │   └── utils/
│       ├── hooks/
│       ├── stores/
│       ├── types/             # tipos espelhando os schemas do backend
│       └── styles/globals.css # tokens de design (cores, radius, tipografia)
│
├── backend/
│   ├── pyproject.toml · uv.lock · alembic.ini · Dockerfile
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py                     # app factory, middlewares, routers
│   │   ├── core/                       # config.py, logging.py, security.py (JWT), exceptions.py, rate_limit.py
│   │   ├── api/
│   │   │   ├── deps.py                 # get_current_user, get_db
│   │   │   └── v1/                     # documents.py, folders.py, conversations.py,
│   │   │                               # analyses.py, search.py, stats.py, me.py, health.py
│   │   ├── db/
│   │   │   ├── session.py · base.py
│   │   │   └── models/                 # um arquivo por agregado
│   │   ├── schemas/                    # Pydantic (request/response)
│   │   ├── services/                   # regras de negócio: documents, folders, conversations, analyses, stats
│   │   ├── processing/                 # pdf_extractor.py, validator.py, chunker.py, pipeline.py, jobs.py
│   │   ├── ai/
│   │   │   ├── openrouter.py           # cliente HTTP (chat + embeddings)
│   │   │   ├── embeddings.py           # interface + implementação OpenRouter
│   │   │   ├── retrieval.py            # busca híbrida + RRF
│   │   │   ├── rag.py                  # orquestra pergunta → resposta + citações
│   │   │   ├── prompts/                # templates PT-BR (chat, resumo, comparação, extração)
│   │   │   └── guards.py               # validação de citações, abstenção
│   │   └── storage/                    # base.py, supabase_storage.py, local_storage.py
│   └── tests/
│       ├── conftest.py                 # banco de teste, usuário fake, mocks do OpenRouter
│       ├── unit/                       # chunker, validator, guards, rrf
│       └── api/                        # rotas end-to-end com AsyncClient
│
└── supabase/
    ├── storage.sql                     # bucket "documents" + políticas
    └── README.md                       # como configurar o projeto Supabase
```

---

## 4. Modelo de dados

Todas as tabelas em `public`, `user_id` referenciando `auth.users(id)` do Supabase, RLS ativo.

```
auth.users (Supabase) 1──1 profiles
profiles 1──* folders 1──* documents 1──* document_pages
                               │
                               ├──* document_chunks  (embedding vector, tsv)
                               ├──* processing_jobs
                               └──* conversation_documents *──1 conversations 1──* messages 1──* message_citations
profiles 1──* analyses (resumo / extração / comparação)
profiles 1──* usage_events
```

| Tabela | Colunas principais | Notas |
|---|---|---|
| `profiles` | `id uuid PK → auth.users`, `full_name`, `avatar_url`, `created_at` | Criada por trigger no cadastro |
| `folders` | `id`, `user_id`, `name`, `color`, `parent_id null`, `created_at` | Hierarquia simples (1 nível na UI, modelo permite mais) |
| `documents` | `id`, `user_id`, `folder_id null`, `title`, `original_filename`, `storage_path`, `file_size`, `sha256`, `page_count`, `status enum(uploaded, processing, ready, failed)`, `processed_pages`, `error_message`, `processed_at`, `created_at`, `updated_at` | `UNIQUE(user_id, sha256)` evita duplicatas |
| `document_pages` | `id`, `document_id`, `page_number`, `text`, `char_count` | Permite exibir a página fonte e reprocessar sem reextrair |
| `document_chunks` | `id`, `document_id`, `user_id`, `page_number`, `chunk_index`, `content`, `token_count`, `embedding vector(EMBEDDING_DIM)`, `tsv tsvector GENERATED (portuguese)`, `metadata jsonb` | Índices: HNSW cosine em `embedding`, GIN em `tsv`, btree `(document_id, page_number)` |
| `processing_jobs` | `id`, `document_id`, `status enum(queued, running, done, failed)`, `attempts`, `last_error`, `created_at`, `started_at`, `finished_at` | Durável: jobs `queued/running` são retomados ao reiniciar a API |
| `conversations` | `id`, `user_id`, `title`, `created_at`, `updated_at` | Título gerado a partir da 1ª pergunta |
| `conversation_documents` | `conversation_id`, `document_id` (PK composta) | Uma conversa pode cobrir N documentos |
| `messages` | `id`, `conversation_id`, `role enum(user, assistant)`, `content`, `model`, `prompt_tokens`, `completion_tokens`, `created_at` | — |
| `message_citations` | `id`, `message_id`, `chunk_id`, `document_id`, `page_number`, `excerpt`, `score`, `rank` | O que o frontend usa para "fontes" e abrir a página |
| `analyses` | `id`, `user_id`, `type enum(summary, key_info, comparison)`, `document_ids uuid[]`, `content`, `model`, `created_at` | Resumos/extrações/comparações persistidos e exportáveis (Markdown/PDF) |
| `usage_events` | `id`, `user_id`, `kind enum(upload, question, summary, key_info, comparison, search)`, `document_id null`, `prompt_tokens`, `completion_tokens`, `created_at` | Alimenta o dashboard de estatísticas |

Busca semântica global (fora do chat) usa `document_chunks` filtrado por `user_id` e, opcionalmente, por pasta.

---

## 5. Endpoints (resumo)

| Método | Rota | Função |
|---|---|---|
| GET | `/api/v1/health` | Status da API, banco e OpenRouter |
| GET | `/api/v1/me` | Perfil do usuário autenticado |
| GET/POST | `/api/v1/folders` · PATCH/DELETE `/folders/{id}` | Pastas |
| POST | `/api/v1/documents` (multipart) | Upload + enfileira processamento |
| GET | `/api/v1/documents?folder_id&status&q` | Lista com filtros |
| GET/PATCH/DELETE | `/api/v1/documents/{id}` | Detalhe (status, progresso), renomear/mover, excluir (storage + banco) |
| GET | `/api/v1/documents/{id}/pages/{n}` · `/file` | Texto da página · URL assinada do PDF |
| POST | `/api/v1/documents/{id}/reprocess` | Reexecuta pipeline |
| GET/POST | `/api/v1/conversations` · GET/DELETE `/{id}` | Conversas |
| POST | `/api/v1/conversations/{id}/messages` (SSE) | Pergunta → stream de tokens + evento `citations` |
| POST | `/api/v1/analyses/summary` · `/key-info` · `/comparison` | Recursos adicionais |
| GET | `/api/v1/analyses/{id}/export?format=md\|pdf` | Exportação |
| GET | `/api/v1/search?q=&folder_id=` | Busca semântica global |
| GET | `/api/v1/stats/overview` | Dashboard |

Autenticação (cadastro, login, logout, reset) acontece no frontend contra o Supabase; o backend não tem rotas de senha.

---

## 6. Identidade visual (direção)

- **Marca:** DocuMind AI; símbolo = documento com um "nó" de rede (ícone próprio em SVG).
- **Paleta:** fundo escuro profundo (`#0B0E14`), superfícies em camadas (`#121620`, `#1A1F2B`), acento **índigo-violeta** (`#7C6CF6`) com secundário **ciano** (`#34D5C8`) para citações/fontes; tema claro espelhado com tokens CSS.
- **Tipografia:** Inter (UI) + JetBrains Mono (trechos citados, números de página).
- **Padrões:** sidebar recolhível, cards com borda sutil (sem sombras pesadas), skeletons em toda lista, empty states ilustrados com CTA, toasts discretos, animações de 150–200 ms, chat com painel lateral de fontes que destaca a página.
- **Responsivo:** sidebar vira drawer abaixo de 1024 px; chat ocupa a tela toda no celular, com fontes em bottom sheet.

---

## 7. Roadmap

| Fase | Entregas | Critério de pronto (verificável) |
|---|---|---|
| **1 · Planejamento** (este doc) | Ambiente, arquitetura, pastas, modelo de dados, roadmap | Aprovação do usuário |
| **2 · Fundação** | Monorepo; backend FastAPI com config/logs/exceções/JWT; Alembic + migração inicial (extensões, tabelas, RLS); frontend Next.js com design tokens, layout (sidebar/tema), páginas de auth completas; `.env.example`; docker-compose; CI | Cadastro → e-mail → login → `/dashboard` protegido → `GET /me` retornando o usuário; `pytest` e `vitest` verdes |
| **3 · Núcleo** | Upload + validação + storage; pipeline PyMuPDF → chunks → embeddings → pgvector com jobs e progresso; busca híbrida; RAG com streaming, citações e abstenção; chat persistente | Subir um PDF real, perguntar, receber resposta em PT-BR com páginas citadas; pergunta fora do documento → abstenção; testes do chunker, do RRF, dos guards e das rotas |
| **4 · Experiência** | Dashboard com estatísticas; gestão de documentos (pastas, status, exclusão, visualizador de página); chat refinado (fontes, histórico, multi-documento); resumos, extração, comparação, busca semântica, exportação; responsividade | Checklist de UX (skeleton, empty states, toasts, 3 breakpoints) validado no navegador |
| **5 · Finalização** | Suíte de testes completa; revisão de segurança (upload, RLS, rate limit, headers); README com screenshots e guia de deploy (Vercel + Render/Fly/Railway + Supabase); documentação das ADRs | CI verde, deploy reproduzível a partir do README |

Ordem interna da FASE 2 (primeiros passos após aprovação): instalar pré-requisitos → criar projeto Supabase e
`.env` → esqueleto do backend com `/health` → migração inicial → esqueleto do frontend com auth → CI.

---

## 8. Riscos e limitações conhecidas

| Risco | Mitigação |
|---|---|
| PDFs escaneados (imagem, sem texto) | Detectado na extração; documento marcado `failed` com mensagem clara. OCR (Tesseract) fica como extensão futura, fora do escopo inicial |
| Dimensão do embedding varia por modelo | `EMBEDDING_DIM` validado contra o modelo no startup; troca de modelo exige reprocessar (documentado) |
| Projeto Supabase gratuito pausa após inatividade | Documentado no README; sem impacto no código |
| Custo de tokens do OpenRouter | Modelos padrão econômicos, tokens registrados em `usage_events`, limite de contexto por pergunta |
| Sem Docker na máquina | Fluxo de dev não depende dele; imagens testadas na FASE 5 ou via CI |
