#!/usr/bin/env bash
# OligoFormer off-target 内网 SaaS —— 生产启动脚本
# 使用 oligolab 后端轻量 venv 跑 FastAPI，重型推理交给 oligorunner conda 环境。
set -euo pipefail

# 脚本所在目录（service/），运行时切进去，保证 uvicorn 能 import app.main
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# off-target 模块根（service 的上一级），用于定位 PerlLib
OFFTARGET_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PY="/export/projects/sandbox/oligolab/.venv/bin/python"
PORT="${OFFTARGET_PORT:-7131}"

export OFFTARGET_PORT="$PORT"
# 推理在该 conda 环境执行（config.CONDA_PYTHON 默认已指向它，可被环境变量覆盖）
export OLIGORUNNER_PYTHON="${OLIGORUNNER_PYTHON:-/home/aiuser/.conda/envs/oligorunner/bin/python}"
# 脱靶 perl 模块
export PERL5LIB="$OFFTARGET_DIR/PerlLib:${PERL5LIB:-}"

echo "[offtarget] starting on 127.0.0.1:$PORT (python=$PY, cwd=$PWD)"
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" "$@"
