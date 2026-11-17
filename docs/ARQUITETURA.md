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

**Decisão:** arquivos em bucket privado, acessados só pelo backend com a service role, atrás da
interface `StorageBackend` (`app/storage`), com implementação Supabase e uma local em disco.
**Revisão na FASE 3:** o download do PDF original passa pelo backend (`GET /documents/{id}/file`)
em vez de URL assinada. Motivo: a posse é verificada em toda leitura, nada do bucket é exposto e o
mesmo código funciona com o armazenamento local. URLs assinadas ficam como otimização futura se o
tráfego de arquivos crescer.
**Caminhos** seguem `<user_id>/<document_id>.pdf` e são validados por regex contra path traversal.

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
**Implementação (FASE 3, `app/ai/retrieval.py` e `app/ai/rag.py`):**
- Um trecho só entra no contexto se a similaridade vetorial for ≥ `RAG_MIN_SIMILARITY` **ou** se
  todos os termos da busca aparecerem nele (full-text). No máximo 2 trechos por página, para
  diversificar as fontes; o total respeita `RAG_CONTEXT_TOKENS`.
- Sem trechos aprovados, a resposta é a frase padrão de ausência e o LLM não é chamado.
- Em conversas com histórico, a pergunta é reescrita como autônoma (só para a busca); o histórico
  vai inteiro para o modelo.
- O prompt numera os trechos (`[n] Documento "X", página Y`), exige citação por afirmação, manda
  tratar o conteúdo dos trechos como dados (defesa contra prompt injection nos PDFs) e define a
  frase exata de abstenção.
- Depois do streaming, `app/ai/guards.py` remove citações inexistentes, normaliza `[1, 2]` para
  `[1][2]` e só persiste como fonte o que foi efetivamente citado.

## ADR-013 — Provedores de IA atrás de protocolos

**Decisão:** o pipeline e o RAG dependem de `EmbeddingProvider` e `ChatProvider`
(`app/ai/providers.py`); `OpenRouterClient` é a implementação real e `create_app()` aceita outras.
**Motivo:** trocar de gateway sem mexer no núcleo e testar o fluxo inteiro sem rede.
**Consequência:** os testes usam provedores determinísticos que ficam só em `tests/fakes.py` e
nunca são usados pela aplicação.

## ADR-014 — Testes de integração contra Postgres real

**Decisão:** além dos testes unitários, a suíte roda contra um Postgres com pgvector quando
`TEST_DATABASE_URL` existe: recria o schema, aplica as migrações do Alembic e exercita upload,
pipeline, SQL vetorial, full-text, SSE, citações e isolamento entre usuários.
**Motivo:** a parte mais arriscada (SQL vetorial, `tsvector`, cascatas, jobs) não se testa com mocks.
**Como rodar localmente sem Docker:** o pacote `pgserver` (Postgres + pgvector embutidos via pip)
funciona inclusive no Windows; no CI, o serviço `pgvector/pgvector:pg16`.

## ADR-015 — Resposta em SSE com contrato de eventos explícito

**Decisão:** `status` → `token`* → `done` | `error`, documentado em [API.md](API.md). O evento
`done` carrega a mensagem persistida e validada, que substitui o texto do stream no cliente.
**Motivo:** o usuário vê a resposta nascendo, mas o que fica salvo e exibido no fim é a versão
saneada. O gerador usa sessões de banco próprias, independentes do ciclo da requisição.

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
