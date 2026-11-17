# Configuração do Supabase

O DocuMind AI usa o Supabase para **autenticação**, **banco de dados (Postgres + pgvector)** e
**armazenamento de arquivos**. Todo o schema de dados é aplicado pelo Alembic (backend); aqui ficam
apenas os passos manuais no painel.

## 1. Criar o projeto

1. Acesse https://supabase.com/dashboard e crie um projeto (plano gratuito basta).
2. Guarde a senha do banco: ela entra na connection string.

## 2. Obter as chaves

Em **Project Settings → API**:

| Variável | Onde |
|---|---|
| `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Project Settings → API Keys → **Publishable key** (`sb_publishable_...`); em projetos antigos, a `anon` legada |
| `SUPABASE_SERVICE_ROLE_KEY` | Project Settings → API Keys → **Secret keys** → `default` (`sb_secret_...`), botão de copiar; em projetos antigos, a `service_role` legada. **Só no backend** |
| `SUPABASE_JWT_SECRET` (opcional) | JWT Settings → JWT Secret. Se o projeto usa chaves assimétricas, deixe vazio: o backend valida pelo JWKS |

Em **Project Settings → Database → Connection string**:

| Variável | Onde |
|---|---|
| `DATABASE_URL` | Aba *URI*, modo **Transaction** (porta 6543) ou **Session** (5432). Substitua `[YOUR-PASSWORD]` |

## 3. Autenticação

Em **Authentication → URL Configuration**:

- **Site URL:** `http://localhost:3000` (em produção, a URL do frontend)
- **Redirect URLs:** adicione `http://localhost:3000/auth/callback` (e a equivalente em produção)

Em **Authentication → Providers → Email**, mantenha *Confirm email* ativo para o fluxo de
confirmação por e-mail. Os e-mails de confirmação e de recuperação de senha apontam para
`/auth/callback`, que troca o código por sessão e redireciona.

## 4. Bucket de arquivos (usado a partir da FASE 3)

Execute `storage.sql` no **SQL Editor** do painel. Ele cria o bucket privado `documents` e as
políticas que permitem a cada usuário acessar apenas a própria pasta (`<user_id>/...`).

## 5. Aplicar o schema

Com o `.env` preenchido na raiz do projeto:

```bash
cd backend
uv run alembic upgrade head
```

A migração ativa a extensão `vector`, cria as tabelas, índices (HNSW + GIN) e políticas RLS.

## 6. Verificar tudo

```bash
cd backend
uv run python scripts/check_setup.py
```

O verificador testa, contra os serviços reais e sem imprimir segredos: variáveis do backend e do
frontend, conexão com o banco, pgvector, migrações, dimensão do vetor, Supabase Auth, validação de
JWT, bucket privado (com envio, leitura e exclusão de um arquivo de teste) e OpenRouter (chave, um
embedding e uma resposta mínima de chat, custo de frações de centavo). Use `--skip-ai` para pular
as chamadas aos modelos. Cada falha vem com a correção sugerida.
