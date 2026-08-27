"""OligoFormer 内网 SaaS —— FastAPI 入口。

提供：
  - 网页 UI（提交 mRNA 序列，触发 OligoFormer 推理）
  - REST API：提交 / 查询 / 取消 推理任务
  - /health 健康检查
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .runner import manager

app = FastAPI(title="OligoFormer Off-target SaaS", version="1.0.0")


# ---------- 请求/响应模型 ----------
class PredictRequest(BaseModel):
    sequence: str
    name: str = "RNA"
    with_off_target: bool = False
    with_toxicity: bool = False
    no_func: bool = False
    top_n: int = -1


# ---------- 静态 UI ----------
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>OligoFormer SaaS</h1><p>static/index.html 缺失</p>")


@app.get("/health")
async def health():
    return {"status": "ok", "app": "oligoformer-offtarget", "env_python": config.CONDA_PYTHON}


# ---------- API ----------
@app.post("/api/predict")
async def predict(req: PredictRequest) -> dict[str, Any]:
    seq = req.sequence.strip().upper().replace("T", "U").replace(" ", "")
    if len(seq) < 19:
        raise HTTPException(status_code=400, detail="mRNA 序列长度须 >= 19 nt")
    options = {
        "with_off_target": req.with_off_target,
        "with_toxicity": req.with_toxicity,
        "no_func": req.no_func,
        "top_n": req.top_n,
    }
    job = await manager.submit(sequence=seq, name=req.name or "RNA", options=options)
    return {"job_id": job.id, "status": job.status}


@app.get("/api/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    return [_job_public(j) for j in manager.list_jobs()]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _job_public(job)


def _job_public(job) -> dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "name": job.name,
        "options": job.options,
        "result": job.result,
        "summary": job.summary,
        "error": job.error,
    }
