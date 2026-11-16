# DocuMind AI — Frontend

Next.js 15 (App Router) + TypeScript + Tailwind CSS 4, autenticação via Supabase (`@supabase/ssr`).

## Executar

```bash
pnpm install
cp .env.local.example .env.local   # preencha com a URL e a chave anon do Supabase
pnpm dev                           # http://localhost:3000
```

## Qualidade

```bash
pnpm typecheck
pnpm test
pnpm build
```

## Estrutura

- `src/app/(auth)` — login, cadastro, recuperação e redefinição de senha
- `src/app/(app)` — áreas autenticadas (dashboard, documentos, conversas, …)
- `src/app/auth/callback` — troca do código dos e-mails do Supabase por sessão
- `src/components/ui` — design system próprio (botão, input, card, skeleton, badge, alert, logo)
- `src/components/layout` — sidebar, topbar, tema, empty state
- `src/lib/supabase` — clientes para navegador, servidor e middleware
- `src/lib/api` — cliente tipado do backend com token Bearer
- `src/middleware.ts` — renovação de sessão e proteção de rotas
