"""OligoLab FastAPI entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db
from app.middleware.auth import AuthMiddleware
from app.routers import auth, modules, health, literature


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(auth.router)
app.include_router(modules.router)
app.include_router(health.router)
app.include_router(literature.router)

# 文献与知识库：md 文档图片等资源静态目录
# 路径形如 /literature/assets/<文档名>/xxx.png（img 标签直连，无需 JWT）
_LIT_ROOT = Path(settings.LITERATURE_DOCS_DIR).resolve()
if _LIT_ROOT.is_dir():
    app.mount(
        "/literature/assets",
        StaticFiles(directory=str(_LIT_ROOT)),
        name="literature_assets",
    )

# 托管前端构建产物（若存在）
DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "status": "ok"}
