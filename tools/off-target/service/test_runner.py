"""OligoFormer off-target SaaS —— 核心推理单元测试。

用例通过真实调用 OligoFormer 推理（RNA-FM + transformer），验证：
  1. 环境可运行（GPU / 依赖）与端到端产物生成
  2. 结果解析正确（列、数量、排序）
  3. 只做结构与 sanity 断言，不断言具体数值

运行（在 service/ 目录）：
  /home/aiuser/.conda/envs/oligorunner/bin/python -m pytest test_runner.py -v
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.runner import run_inference

EXAMPLE_SEQ = "GGUUCAAUUUAAUUUGCGAAAGAGACCUUACGGACGUGGGCGCCAGUGGACCUCCUC"


def test_environment_python_ok():
    """oligorunner 环境里 torch+CUDA 可用。"""
    import torch

    assert torch.cuda.is_available(), "需要可用 GPU (H20)"


def test_run_inference_core():
    """核心疗效预测：无 off-target/tox，应返回按 efficacy 排序的行。"""
    rows, summary, _ = run_inference(EXAMPLE_SEQ, "testRNA", {})
    assert rows, "应产生非空结果"
    first = rows[0]
    assert "sense" in first and "siRNA" in first and "efficacy" in first
    # 排序：efficacy 降序
    effs = [float(r["efficacy"]) for r in rows if r.get("efficacy")]
    assert effs == sorted(effs, reverse=True), "应按 efficacy 降序排列"
    # sanity：缩放后 efficacy 应落在合理区间
    assert all(0.0 <= e <= 2.0 for e in effs), f"efficacy 越界: {effs}"
    assert summary["siRNA_count"] == len(rows)


def test_run_inference_disable_filters():
    """关掉功能过滤器（-nf）时仍能出结果。"""
    rows, _, _ = run_inference(EXAMPLE_SEQ, "testRNA_nf", {"no_func": True})
    assert rows


def test_result_files_written():
    """确认结果文件确实落盘。"""
    _, _, raw = run_inference(EXAMPLE_SEQ, "testRNA_files", {})
    ranked = raw.get("ranked")
    assert ranked, "应有 ranked 结果文件路径"
    assert Path(ranked).exists(), f"结果文件不存在: {ranked}"


# ---------------------------------------------------------------------------
# 以下为重型集成用例（每个 ~7-9 分钟，默认跳过；CI 中可用 --runslow 开启）
# ---------------------------------------------------------------------------
def _skip_in_ci() -> bool:
    return not bool(os.environ.get("RUNSLOW"))

@pytest.mark.skipif(_skip_in_ci(), reason="heavy integration (off-target scan ~8min)")
def test_integration_off_target_toxicity():
    """脱靶(PITA/TargetScan) + 毒性 全链路。"""
    rows, _, _ = run_inference(
        EXAMPLE_SEQ, "testRNA_offtox",
        {"with_off_target": True, "with_toxicity": True},
    )
    assert rows
    cols = set(rows[0].keys())
    for c in ("pita_score", "targetscan_score", "off_target_filter",
              "cell_viability", "toxicity_filter"):
        assert c in cols, f"缺少列 {c}"
