# API do DocuMind AI

Base: `/api/v1`. A documentação interativa (OpenAPI) fica em `http://localhost:8000/docs` fora de
produção. Todas as rotas, exceto `/health`, exigem o token do Supabase Auth:

```
Authorization: Bearer <access_token>
```

## Erros

Toda resposta de erro segue o mesmo envelope:

```json
{ "error": { "code": "not_found", "message": "Documento não encontrado.", "details": {} } }
```

| HTTP | `code` | Quando |
|---|---|---|
| 401 | `unauthorized` | Token ausente, inválido ou expirado |
| 404 | `not_found` | Recurso inexistente **ou de outro usuário** (nunca 403, para não revelar existência) |
| 409 | `conflict` | PDF já enviado pelo mesmo usuário (`details.document_id`), reprocessamento em andamento |
| 413 | `payload_too_large` | Arquivo acima de `MAX_UPLOAD_MB` |
| 422 | `unprocessable` / `validation_error` | PDF inválido, protegido por senha, páginas demais, dados inválidos |
| 429 | `rate_limited` | Muitas requisições (upload e perguntas: 30/min por usuário) |
| 502 | `external_service_error` / `storage_error` | Falha no OpenRouter ou no Storage |

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API e do banco; indica se OpenRouter e Storage estão configurados |
| GET / PATCH | `/me` | Perfil do usuário (criado no primeiro acesso) |
| POST | `/documents` | Upload multipart (`file`). Valida, grava no storage e agenda o processamento. `201` |
| GET | `/documents?status=&q=` | Lista do usuário, mais recentes primeiro |
| GET | `/documents/{id}` | Detalhe com `status`, `processed_pages`, `progress` (0–1) e `error_message` |
| PATCH | `/documents/{id}` | Renomeia (`{"title": "..."}`) |
| DELETE | `/documents/{id}` | Remove registro, páginas, chunks, citações e o arquivo. `204` |
| POST | `/documents/{id}/reprocess` | Reexecuta extração, chunking e embeddings. `202` |
| GET | `/documents/{id}/pages/{n}` | Texto extraído da página `n` |
| GET | `/documents/{id}/file` | PDF original (`application/pdf`), após checagem de posse |
| POST | `/conversations` | Cria conversa: `{"document_ids": [...]}` (lista vazia = toda a biblioteca) |
| GET | `/conversations` | Lista, mais recentes primeiro |
| GET | `/conversations/{id}` | Histórico com mensagens e citações |
| PATCH / DELETE | `/conversations/{id}` | Renomeia / exclui |
| POST | `/conversations/{id}/messages` | Pergunta `{"content": "..."}` com resposta em **SSE** |

## Status do documento

`uploaded` (na fila) → `processing` → `ready` | `failed`. Falhas transitórias do OpenRouter ou do
Storage são retentadas até `JOB_MAX_ATTEMPTS` vezes; problemas do arquivo (por exemplo, PDF
digitalizado sem texto) falham na hora, com a mensagem em `error_message`.

## Streaming da resposta (SSE)

`POST /conversations/{id}/messages` responde `text/event-stream`. Cada evento é uma linha
`data: <json>` seguida de linha em branco:

```text
data: {"type": "status", "stage": "retrieving"}

data: {"type": "status", "stage": "generating", "sources": 4}

data: {"type": "token", "delta": "O prazo de vigência é de 24 meses "}

data: {"type": "token", "delta": "[1]."}

data: {"type": "done", "abstained": false, "grounded": true, "message": {
  "id": "…", "role": "assistant", "content": "O prazo de vigência é de 24 meses [1].",
  "created_at": "…",
  "citations": [{"id": "…", "rank": 1, "document_id": "…", "document_title": "Contrato",
                 "page_number": 2, "excerpt": "Cláusula 2. O prazo…", "score": 0.71}]
}}
```

- `token`: pedaços do texto à medida que o modelo gera.
- `done.message`: a versão **persistida e validada** da resposta. Citações para trechos que não
  foram enviados ao modelo são removidas; por isso o cliente deve substituir o texto do stream
  pelo `content` final.
- `citations[].rank` corresponde ao marcador `[rank]` no texto.
- `abstained: true`: nenhum trecho relevante, ou o modelo declarou não encontrar a informação. O
  conteúdo é a frase padrão de ausência e o LLM nem é chamado quando a recuperação não acha nada.
- `error`: `{"type": "error", "code": "...", "message": "..."}`. A pergunta já foi salva no histórico.
