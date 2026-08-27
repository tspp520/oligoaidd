#!/usr/bin/env bash
# OligoFormer off-target 内网 SaaS —— 开发启动（热重载）
set -euo pipefail
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export OFFTARGET_PORT="${OFFTARGET_PORT:-7131}"
export OLIGORUNNER_PYTHON="${OLIGORUNNER_PYTHON:-/home/aiuser/.conda/envs/oligorunner/bin/python}"
export PERL5LIB="$SERVICE_DIR/../PerlLib:${PERL5LIB:-}"
exec /export/projects/sandbox/oligolab/.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port "${OFFTARGET_PORT:-7131}" --reload
