# Arquitetura e decisões (ADRs)

Documento vivo. Cada decisão registra contexto, alternativas e consequências. O diagrama geral e o
modelo de dados estão em [FASE1-PLANEJAMENTO.md](FASE1-PLANEJAMENTO.md).

## ADR-001 — Monorepo

**Decisão:** um único repositório com `frontend/`, `backend/`, `supabase/` e `docs/`.
**Motivo:** um clone, um CI, documentação única; facilita apresentar o projeto em portfólio.
**Consequência:** cada parte mantém seu próprio gerenciador (pnpm / uv) e seu Dockerfile.

## ADR-002 — Supabase Auth; o backend apenas valida o JWT

**Decisão:** cadastro, login, logout e recuperação de senha acontecem no frontend contra o Supabase
Auth. O backend não tem rotas de senha: valida assinatura, expiração e audiência do token em toda
requisição (`app/core/security.py`) e extrai o `user_id`.
**Suporte a dois esquemas:** HS256 com `SUPABASE_JWT_SECRET` (legado) ou chaves assimétricas via
JWKS público do projeto quando o segredo não é informado.
**Consequência:** zero senhas armazenadas por nós; o perfil (`profiles`) é criado de forma
preguiçosa no primeiro acesso autenticado (`services/profiles.ensure_profile`), sem depender de
triggers no schema `auth`.

## ADR-003 — Acesso direto ao Postgres com SQLAlchemy async

**Decisão:** o backend conecta ao Postgres do Supabase pela connection string (asyncpg), não pela
API REST do Supabase.
**Motivo:** controle total do SQL vetorial (`<=>`, HNSW) e da busca híbrida com `tsvector`.
**Consequência:** compatibilidade com o pooler em modo transação exige desativar o cache de
prepared statements (`db/session.py`).

## ADR-004 — Alembic como única fonte de verdade do schema

**Decisão:** extensões, tabelas, índices, triggers e políticas RLS vivem nas migrações do Alembic.
**Motivo:** versionamento junto do código; reproduzível em qualquer Postgres com pgvector (inclusive
o do `docker-compose.yml`).
**Consequência:** a migração inicial cria um `auth.uid()` de compatibilidade apenas quando ele não
existe (fora do Supabase). A dimensão do vetor vem de `EMBEDDING_DIM`; trocá-la exige nova migração
e reprocessamento dos documentos.

## ADR-005 — Supabase Storage para PDFs (adapter trocável)

**Decisão:** arquivos em bucket privado, acessados pelo backend com a service role e entregues ao
usuário por URL assinada de curta duração. Interface `StorageBackend` (FASE 3) com implementação
local em disco para testes.

## ADR-006 — OpenRouter para chat e embeddings via httpx

**Decisão:** chamadas diretas aos endpoints compatíveis com OpenAI do OpenRouter, com retry
exponencial e timeout. Modelos configuráveis por ambiente (`LLM_MODEL`, `EMBEDDING_MODEL`).

## ADR-007 — Processamento em background no próprio serviço, com jobs duráveis

**Decisão:** tabela `processing_jobs` + tarefas asyncio no processo da API. Jobs `queued/running`
são retomados no startup.
**Alternativa rejeitada por ora:** Celery/arq + Redis (infra extra desnecessária no início).
**Consequência:** a interface `JobRunner` (FASE 3) permite plugar um worker externo sem alterar os
serviços.

## ADR-008 — Busca híbrida com RRF e abstenção

**Decisão:** top-k vetorial (cosine) ⊕ top-k full-text em português, combinados por Reciprocal Rank
Fusion; score mínimo antes de chamar o LLM; citações validadas contra os trechos enviados.
**Motivo:** termos exatos (cláusulas, siglas, números) se beneficiam do full-text; a abstenção evita
respostas inventadas.

## ADR-009 — Isolamento por usuário em três camadas

1. Filtro por `user_id` em toda consulta do backend (404 para recursos de outros usuários).
2. RLS ativo em todas as tabelas (protege o acesso direto pela API do Supabase).
3. Bucket privado com políticas por usuário.

## ADR-010 — Erros com envelope único e logs estruturados

**Decisão:** toda resposta de erro segue `{"error": {"code", "message", "details?"}}`
(`core/exceptions.py`); logs JSON em produção com `request_id` por requisição (`core/logging.py`).

## ADR-011 — Design system próprio no frontend

**Decisão:** componentes de UI escritos no projeto (sem biblioteca de componentes pronta), tokens de
cor em CSS variables com tema escuro padrão e claro opcional (`styles/globals.css`).
**Motivo:** identidade visual própria, exigência do produto; bundle menor.
**Consequência:** o `Button` implementa `asChild` sem Radix para estilizar `<Link>`.

## ADR-012 — Proteção de rotas em duas camadas no Next.js

**Decisão:** o middleware renova a sessão e redireciona rotas protegidas; o layout `(app)` valida o
usuário no servidor novamente antes de renderizar.
**Motivo:** o middleware roda no edge e pode ser contornado por configuração; a validação no layout
garante a proteção mesmo assim e evita flash de conteúdo.
