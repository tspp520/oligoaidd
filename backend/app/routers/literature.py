"""文献与知识库 —— Markdown 文档库。

目录约定：`literature_docs/` 下每个文档一个同名子文件夹，
子文件夹内含 `<名字>.md` 及该文档引用到的图片等资源。

- GET /api/literature/docs            -> 列出文档（子文件夹名）
- GET /api/literature/docs/{name}     -> 返回该文档 md 原文
图片等资源由 main.py 以 StaticFiles 挂载在 /literature/assets 下公开访问。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/api", tags=["literature"])

DOCS_ROOT = Path(settings.LITERATURE_DOCS_DIR).resolve()


def _resolve_doc_dir(name: str) -> Path:
    """安全解析文档子目录，防目录穿越。"""
    target = (DOCS_ROOT / name).resolve()
    if not str(target).startswith(str(DOCS_ROOT) + "/"):
        raise HTTPException(status_code=400, detail="非法文档名")
    return target


def _find_md(doc_dir: Path, name: str) -> Path | None:
    """优先取与子文件夹同名 .md，否则取目录内第一个 .md。"""
    cand = doc_dir / f"{name}.md"
    if cand.is_file():
        return cand
    for p in sorted(doc_dir.glob("*.md")):
        return p
    return None


@router.get("/literature/docs")
async def list_docs():
    """列出所有文档（子文件夹名，即栏目名）。"""
    if not DOCS_ROOT.is_dir():
        return {"docs": []}
    docs = []
    for d in DOCS_ROOT.iterdir():
        if d.is_dir() and _find_md(d, d.name) is not None:
            m = d.stat().st_mtime
            docs.append({"name": d.name, "updated": datetime.fromtimestamp(m).isoformat()})
    docs.sort(key=lambda x: x["name"])
    return {"docs": docs}


@router.get("/literature/docs/{name}")
async def get_doc(name: str):
    """返回指定文档的 md 原文。"""
    doc_dir = _resolve_doc_dir(name)
    md_file = _find_md(doc_dir, name)
    if md_file is None:
        raise HTTPException(status_code=404, detail=f"文档不存在: {name}")
    content = md_file.read_text(encoding="utf-8")
    return {"name": name, "content": content}
