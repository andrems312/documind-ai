# Revisão de segurança — DocuMind AI

> Revisão da postura de segurança da aplicação. Última atualização: 2026-11-19.
> Escopo: backend (FastAPI), frontend (Next.js) e a integração com Supabase e OpenRouter.

## 1. Objetivo e metodologia

O DocuMind AI é um SaaS multiusuário que recebe PDFs, gera embeddings e responde perguntas
fundamentadas. Como cada usuário envia conteúdo próprio e potencialmente sensível, **o isolamento
entre usuários e o tratamento de segredos são requisitos de primeira ordem**.

A revisão combinou:

- **Leitura dirigida do código** nas áreas de risco (autenticação, autorização, upload, SQL,
  storage, CORS, segredos, prompt injection);
- **Testes automatizados** que exercem os controles — com destaque para um teste que prova o
  isolamento por RLS no nível do banco ([`backend/tests/integration/test_rls.py`](backend/tests/integration/test_rls.py));
- **Verificação contínua** no CI: `ruff`, `mypy` e a suíte de testes a cada push
  ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## 2. Modelo de ameaças (resumido)

| Ativo | Ameaça principal | Mitigação |
|---|---|---|
| Documentos e trechos de um usuário | Acesso por outro usuário | Isolamento em três camadas (§3.2) |
| Chaves (banco, service role, OpenRouter) | Vazamento para o cliente ou para o git | Segredos só no backend; `.env` fora do git (§3.4) |
| Pipeline de upload | PDF malicioso, path traversal, DoS por arquivo enorme | Validação por assinatura, limites e caminho seguro (§3.3) |
| Resposta do LLM | Prompt injection via conteúdo do documento | Conteúdo tratado como dado; citações validadas (§3.9) |
| Endpoints caros (chat, análises, busca) | Abuso / custo | Rate limit por usuário (§3.5) |

## 3. Controles implementados

### 3.1 Autenticação
- O backend **não armazena senhas nem cria sessões**: delega ao Supabase Auth e apenas **valida o
  JWT** em toda rota ([`backend/app/core/security.py`](backend/app/core/security.py)).
- Suporta assinatura **HS256** (segredo) e **chaves assimétricas via JWKS**; exige os claims
  `exp` e `sub` e valida a audiência (`authenticated`). Tokens expirados ou inválidos → `401`.

### 3.2 Autorização — isolamento em três camadas (defesa em profundidade)
1. **Aplicação:** toda query filtra por `user_id`; recursos de outro usuário retornam **`404`, não
   `403`**, para não revelar sua existência ([`backend/app/services/`](backend/app/services/)).
2. **Banco (RLS):** políticas `USING (user_id = auth.uid())` em todas as tabelas de usuário, com
   verificação por `EXISTS` nas tabelas-filhas ([migração inicial](backend/alembic/versions/0001_schema_inicial.py)).
   Um papel sem privilégios, com o claim de um usuário, **só enxerga as linhas desse usuário** —
   provado por teste de integração.
3. **Storage:** bucket privado; políticas restringem cada usuário à própria pasta `<user_id>/…`
   ([`supabase/storage.sql`](supabase/storage.sql)); download só pelo backend após checagem de posse.

### 3.3 Validação de entrada (upload)
- Verificação de **assinatura de bytes** (`%PDF-`), MIME, **tamanho máximo** (lê no máximo
  `limite+1` bytes), **limite de páginas**, detecção de **PDF protegido por senha** e de PDF
  **escaneado sem texto**, além de **dedupe por SHA-256** por usuário
  ([`backend/app/processing/validator.py`](backend/app/processing/validator.py)).
- **Path traversal bloqueado:** o caminho no storage é validado por regex `^<uuid>/<uuid>.pdf$`
  ([`backend/app/storage/base.py`](backend/app/storage/base.py)).

### 3.4 Gestão de segredos
- Segredos (banco, `service_role`, OpenRouter) **só existem no backend**. O frontend recebe apenas
  `NEXT_PUBLIC_SUPABASE_URL`, a chave **publishable** (pública por design) e a URL da API.
- `.env` e `.env.*` estão no `.gitignore`; o `.env.example` não contém valores reais.

### 3.5 Rate limiting
- `slowapi` com chave **por usuário** autenticado (IP como fallback)
  ([`backend/app/core/rate_limit.py`](backend/app/core/rate_limit.py)); limites menores nas rotas
  caras — upload, chat e busca a 30/min; análises a 20/min. Resposta `429` com envelope JSON.

### 3.6 Cabeçalhos de segurança
- Backend e frontend enviam `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy` e `Permissions-Policy` (câmera/microfone/geolocalização desativados);
  **HSTS** apenas em produção. O frontend adiciona uma **CSP** anticlickjacking
  (`frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`, `object-src 'none'`).

### 3.7 CORS
- Origens **restritas** à URL do frontend (sem wildcard), com `allow_credentials`; a lista vem de
  `CORS_ORIGINS` ([`backend/app/main.py`](backend/app/main.py)).

### 3.8 Injeção e SSRF
- **SQL:** acesso via SQLAlchemy com parâmetros vinculados; não há concatenação de entrada do
  usuário em SQL (o único trecho interpolado é um inteiro validado da configuração do HNSW).
- **XSS:** o frontend **não usa `dangerouslySetInnerHTML`**; a resposta do modelo é convertida em
  **estrutura** (parágrafos, listas, citações) e renderizada pelo React, nunca como HTML
  ([`frontend/src/lib/utils/answer-format.ts`](frontend/src/lib/utils/answer-format.ts)).
- **SSRF:** as URLs externas (Storage, OpenRouter) vêm da **configuração**, nunca de entrada do
  usuário.

### 3.9 Defesa contra prompt injection (RAG)
- O prompt de sistema instrui o modelo a **usar somente os trechos fornecidos**, tratar o conteúdo
  dos documentos como **dado** e **ignorar instruções embutidas** neles
  ([`backend/app/ai/prompts.py`](backend/app/ai/prompts.py)).
- As **citações são validadas** contra os trechos realmente enviados: marcadores `[n]` inexistentes
  são removidos antes de persistir ([`backend/app/ai/guards.py`](backend/app/ai/guards.py)). Sem
  trecho relevante, o sistema **abstém-se sem chamar o LLM**.

### 3.10 Observabilidade
- Logs estruturados (JSON em produção) com `request_id` por requisição; **nenhum segredo é
  registrado** em operação normal.

## 4. Verificação automatizada

- **Teste de RLS** provando o isolamento no banco ([`test_rls.py`](backend/tests/integration/test_rls.py)).
- Testes de isolamento entre usuários nas rotas de documentos, conversas, análises e busca.
- **114 testes** no backend e **33** no frontend; CI roda `ruff` (lint + format), `mypy`, a suíte e
  o **build das imagens Docker** a cada push.

## 5. Riscos residuais e fora de escopo

- **Custo do OpenRouter:** uma conta de demonstração com credenciais públicas pode consumir crédito;
  os rate limits por usuário limitam o volume, mas não o custo total. Monitorar o gasto.
- **Cold start (plano gratuito):** o backend hiberna após inatividade; a 1ª requisição pode levar
  ~50s. Não é um risco de segurança, mas afeta a disponibilidade percebida.
- **CSP conservadora:** a política atual cobre clickjacking e `base-uri`/`form-action`, mas ainda
  não restringe `script-src`. Endurecer com _nonce_ é uma evolução natural.
- **OCR / PDFs escaneados:** fora de escopo; o pipeline os rejeita com mensagem clara em vez de
  processar conteúdo não confiável de imagem.
- **DoS volumétrico:** mitigado por rate limit de aplicação, não por proteção de borda (WAF/CDN).

## 6. Recomendações operacionais

- **Rotacionar periodicamente** as chaves do Supabase e do OpenRouter; nunca commitá-las.
- Ativar **2FA** nas contas dos provedores (GitHub, Vercel, Render, Supabase).
- Em produção, manter `APP_ENV=production` (habilita HSTS e desativa a documentação OpenAPI pública).
