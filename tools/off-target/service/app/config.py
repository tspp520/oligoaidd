"""OligoFormer 内网 SaaS —— 配置。"""
from __future__ import annotations

import os
from pathlib import Path

# 本文件: <proj>/tools/off-target/service/app/config.py
# off-target 模块目录: 上三级 (service 的上一级父目录 tools 不对，应取 off-target)
# config.py -> app -> service -> off-target
OFFTARGET_DIR = Path(__file__).resolve().parent.parent.parent  # .../off-target
# OligoFormer 仓库根: off-target/OligoFormer
OLIGOFORMER_DIR = (OFFTARGET_DIR / "OligoFormer").resolve()

# oligorunner conda 环境里的 python 解释器（承载 torch / RNA-FM / infer.py）
CONDA_PYTHON = os.environ.get(
    "OLIGORUNNER_PYTHON",
    "/home/aiuser/.conda/envs/oligorunner/bin/python",
)

# 推理结果输出目录（相对 OligoFormer 根）
RESULT_DIR = OLIGOFORMER_DIR / "result"
DATA_INFER_DIR = OLIGOFORMER_DIR / "data" / "infer"

# 服务参数
HOST = os.environ.get("OFFTARGET_HOST", "127.0.0.1")
PORT = int(os.environ.get("OFFTARGET_PORT", "7131"))
AUTH_ENABLED = os.environ.get("OFFTARGET_AUTH_ENABLED", "false").lower() == "true"

# 并行：OligoFormer 推理很重且依赖同一批工作目录，默认串行执行
MAX_CONCURRENT_JOBS = int(os.environ.get("OFFTARGET_MAX_CONCURRENT", "1"))

# 单次推理（RNA-FM 特征提取 + transformer 打分）超时上限（秒）
JOB_TIMEOUT = int(os.environ.get("OFFTARGET_JOB_TIMEOUT", "1800"))

# 源程序相对 OligoFormer 根的调用名
INFER_MAIN = "scripts/main.py"
