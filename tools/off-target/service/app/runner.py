"""OligoFormer 推理封装 —— 在 oligorunner conda 环境里子进程运行上游 CLI，并解析结果。

设计：OligoFormer 上游代码使用相对路径、且加载 ~1.2GB 的 RNA-FM 权重，最稳妥的接入
方式是“子进程 + 串行队列”，把上游崩溃隔离在 worker 里，SaaS 主进程保持轻量稳定。
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import config


@dataclass
class Job:
    id: str
    status: str = "queued"          # queued | running | done | error
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    name: str | None = None          # mRNA seq 名
    sequence: str | None = None      # mRNA 序列（输入）
    options: dict = field(default_factory=dict)
    result: list | None = None       # 解析后的 siRNA 结果行
    summary: dict = field(default_factory=dict)
    error: str | None = None
    raw_files: dict = field(default_factory=dict)


class InferenceManager:
    """串行执行 OligoFormer 推理的作业管理器。"""

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    def list_jobs(self):
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def submit(self, sequence: str, name: str = "RNA", options: dict | None = None) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], name=name, sequence=sequence, options=options or {})
        self._jobs[job.id] = job
        # 在后台执行（内部用锁保证串行）
        asyncio.create_task(self._run(job))
        return job

    async def _run(self, job: Job) -> None:
        async with self._lock:
            job.status = "running"
            job.started_at = datetime.now().isoformat()
            try:
                seq = job.sequence or ""
                result, summary, raw = await asyncio.to_thread(
                    run_inference,
                    sequence=seq,
                    seq_name=job.name or "RNA",
                    options=job.options,
                )
                job.result = result
                job.summary = summary
                job.raw_files = raw
                job.status = "done"
            except Exception as exc:  # noqa: BLE001 —— 记录到 job，不向外爆
                job.status = "error"
                job.error = str(exc)
            finally:
                job.finished_at = datetime.now().isoformat()


def _write_input_fasta(tmp_dir: Path, sequences: list[tuple[str, str]]) -> Path:
    """把 (name, seq) 列表写成 fasta 文件。"""
    fa = tmp_dir / "mRNA.fa"
    with fa.open("w") as f:
        for name, seq in sequences:
            f.write(f">{name}\n{seq}\n")
    return fa


def run_inference(sequence: str, seq_name: str, options: dict) -> tuple[list, dict, dict]:
    """同步执行一次推理，返回 (结果行列表, 汇总, 原始文件路径)。

    options 可选键：
      - with_off_target: bool   是否跑脱靶 (pita/targetscan, 慢)
      - with_toxicity: bool     是否跑毒性
      - top_n: int              -1 或具体数值
      - output_dir: str         结果输出目录名（默认 result/）
    """
    opt = options or {}
    seq_name_safe = seq_name.replace(" ", "_@_")

    # 临时工作目录：放输入 fasta，并作为本次产出隔离目录
    work_dir = config.OLIGOFORMER_DIR / "data" / "infer" / f"job_{uuid.uuid4().hex[:8]}"
    work_dir.mkdir(parents=True, exist_ok=True)

    fa = _write_input_fasta(work_dir, [(seq_name_safe, sequence)])

    # 结果输出目录
    output_dir = opt.get("output_dir", "result/")
    res_dir = config.OLIGOFORMER_DIR / output_dir
    res_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        config.CONDA_PYTHON,
        config.INFER_MAIN,
        "--infer", "1",
        "-i1", str(fa.relative_to(config.OLIGOFORMER_DIR)),  # infer.py 以仓库根为 cwd
        "--output_dir", output_dir,
    ]
    if opt.get("no_func"):
        cmd += ["-nf"]
    if opt.get("with_off_target"):
        cmd += ["-off", "-a"] if opt.get("all_human") else ["-off"]
        top_n = opt.get("top_n")
        if top_n not in (None, -1):
            cmd += ["-top", str(top_n)]
    if opt.get("with_toxicity"):
        cmd += ["-tox"]

    # 关键：infer.py 里用 os.system('sh scripts/RNA-FM.sh ...') 启动子 shell，
    # 其内部调用裸 `python`。必须把 oligorunner 的 bin 放到 PATH 最前，
    # 否则子 shell 找不到 python（当时踩到的坑）。
    env = dict(os.environ)
    _conda_bin = str(Path(config.CONDA_PYTHON).parent)
    env["PATH"] = _conda_bin + os.pathsep + env.get("PATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    if opt.get("with_off_target"):
        # 脱靶路径的 pita/targetscan 是 perl 脚本，需要 BIO/Statistics 模块。
        perllib = str(config.OFFTARGET_DIR / "PerlLib")
        env["PERL5LIB"] = perllib + os.pathsep + env.get("PERL5LIB", "")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(config.OLIGOFORMER_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=config.JOB_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"推理超时（>{config.JOB_TIMEOUT}s）")

    if proc.returncode != 0:
        raise RuntimeError(
            f"OligoFormer 推理失败 rc={proc.returncode}:\n{proc.stderr[-2000:]}"
        )

    # 解析结果：infer.py 写 result/<name>.txt / _ranked.txt / _ranked_filtered.txt
    result_file = res_dir / f"{seq_name_safe}_ranked.txt"
    rows = _parse_result(result_file)
    if rows is None:
        # 兼容：有些上游版本只写 <name>.txt
        result_file = res_dir / f"{seq_name_safe}.txt"
        rows = _parse_result(result_file)

    summary = {
        "siRNA_count": len(rows) if rows else 0,
        "top_efficacy": rows[0]["efficacy"] if rows else None,
    }
    raw = {
        "ranked": str(res_dir / f"{seq_name_safe}_ranked.txt"),
        "plain": str(res_dir / f"{seq_name_safe}.txt"),
    }
    return (rows or []), summary, raw


def _parse_result(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    rows = []
    with path.open() as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts)))
    return rows


# 模块级单例
manager = InferenceManager()
