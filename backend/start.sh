#!/bin/sh
# Start de produção: aplica as migrações (idempotente) e sobe a API na porta do provedor.
# Usado pelo Render (dockerCommand) e por qualquer `docker run` da imagem do backend.
set -e
/app/.venv/bin/alembic upgrade head
exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
