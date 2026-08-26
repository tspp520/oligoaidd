#!/bin/bash
# OligoLab Backend - Development Mode (uvicorn --reload)
set -e
cd "$(dirname "$0")"
export OLIGOLAB_APP_ENV=development
export OLIGOLAB_DEBUG=true
exec uv run uvicorn app.main:app \
  --app-dir .. \
  --host "${OLIGOLAB_HOST:-127.0.0.1}" \
  --port "${OLIGOLAB_PORT:-7130}" \
  --reload
