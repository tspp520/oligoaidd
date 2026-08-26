#!/bin/bash
# OligoLab Backend - Production Mode (gunicorn multi-worker)
set -e
cd "$(dirname "$0")/.."
export OLIGOLAB_APP_ENV=production
export OLIGOLAB_DEBUG=false
echo "=== OligoLab Backend (PROD) | port ${OLIGOLAB_PORT:-7130} | workers ${OLIGOLAB_WORKERS:-4} ==="
exec uv run gunicorn app.main:app \
  --chdir backend \
  --workers "${OLIGOLAB_WORKERS:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "${OLIGOLAB_HOST:-127.0.0.1}:${OLIGOLAB_PORT:-7130}" \
  --timeout 120
