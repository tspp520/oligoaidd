# OligoLab 小核酸药物内网 SaaS — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一套「小核酸药物研发」内网 SaaS MVP —— 卡片式首页（每卡片新标签页打开模块文字介绍页）+ 公司域账号登录，部署到 `oligolab.chempartner.com:7130`。

**Architecture:** 单 FastAPI 进程托管 React 前端静态产物 + `/api`；nginx 反代 7130。域账号用 LDAP UPN 绑定公司 AD 域，签发 JWT；`/api/*` 受 JWT 中间件保护。数据存公司 Postgres 5434 的独立 `oligolab` 库。

**Tech Stack:** 后端：Python 3.11(uv) + FastAPI + uvicorn/gunicorn + asyncpg + ldap3 + python-jose。前端：React 18 + Vite + TypeScript + axios + react-router-dom + lucide-react。部署：gunicorn 多 worker + systemd + nginx。

## Global Constraints

- 项目根：`/export/projects/sandbox/oligolab/`
- 后端端口：`7130`（本机已确认空闲）
- 域名：`oligolab.chempartner.com` → nginx → 127.0.0.1:7130
- Postgres：`127.0.0.1:5434`，**独立库 `oligolab` / 独立用户 `oligolab`**，严禁读写 complexa 的 `bioarch` 库
- Python 环境：用 `uv`，Python 3.11，较新的稳定依赖（fastapi、uvicorn[standard]、pydantic、pydantic-settings、asyncpg、ldap3、python-jose[cryptography]、gunicorn、loguru、python-multipart、uvicorn-worker）
- 认证：复用 complexa 的 LDAP 方案（UPN 绑定 `CP/CD-GW/CE.shangpharma.com`，host `10.1.1.56:389`，BASE_DN `DC=shangpharma,DC=com`），JWT HS256 7 天，连续 3 次错锁 300 秒；`AUTH_ENABLED` 开关
- 7 个模块 slug：`seq-design` / `off-target` / `structure-properties` / `stability-immuno` / `delivery` / `project-data` / `literature`
- 生产启动：`gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:7130 app.main:app`
- 后端源码统一放到 `backend/`，前端 `frontend/`，nginx `infra/nginx/`
- 所有 SQL 用 asyncpg `$1` 位置参数风格
- 敏感配置（JWT_SECRET、PG 密码、LDAP 密码）只放 `.env`，`.env` 不提交；提供 `.env.example`
- 首次进入实现前需 `git init`（项目当前非 git 仓库）

---

### Task 1: 项目脚手架（git init + uv venv + 目录）

**Files:**
- Create: `/export/projects/sandbox/oligolab/pyproject.toml`
- Create: `/export/projects/sandbox/oligolab/.gitignore`
- Create: `/export/projects/sandbox/oligolab/.env.example`
- Create: `/export/projects/sandbox/oligolab/backend/.keep`
- Create: `/export/projects/sandbox/oligolab/frontend/.keep`
- Create: `/export/projects/sandbox/oligolab/infra/nginx/.keep`
- Create: `/export/projects/sandbox/oligolab/Makefile`

**Interfaces:**
- Consumes: 无
- Produces: uv 管理的 `.venv`（Python 3.11），可供 Task 3 起使用；根目录有 `pyproject.toml` 定义项目元数据。

- [ ] **Step 1: git init + .gitignore**

```bash
cd /export/projects/sandbox/oligolab
git init -b main
```

创建 `.gitignore`：

```gitignore
# python
.venv/
__pycache__/
*.pyc
.env
# node
node_modules/
frontend/dist/
# runtime
logs/
*.log
.DS_Store
```

- [ ] **Step 2: 建目录**

```bash
mkdir -p backend/app/routers backend/app/services frontend infra/nginx docs/superpowers/specs docs/superpowers/plans
touch backend/.keep frontend/.keep infra/nginx/.keep
```

- [ ] **Step 3: 安装 uv 并建立 Python 3.11 venv**

```bash
# 若 uv 未安装
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
cd /export/projects/sandbox/oligolab
# 初始化 pyproject + 建 venv（Python 3.11）
uv init --python 3.11 --package=false
# 指定项目名
uv run python -c "import sys; print(sys.version)"
```

期望输出：以 `3.11.x` 开头的版本号。

- [ ] **Step 4: 创建 .env.example**

```bash
cat > .env.example <<'EOF'
# OligoLab 后端配置模板（复制为 .env 后填写）
OLIGOLAB_APP_NAME=OligoLab
OLIGOLAB_APP_ENV=production
OLIGOLAB_HOST=127.0.0.1
OLIGOLAB_PORT=7130
OLIGOLAB_DEBUG=false
OLIGOLAB_WORKERS=4

# LDAP 域账号
OLIGOLAB_LDAP_HOST=10.1.1.56
OLIGOLAB_LDAP_PORT=389
OLIGOLAB_LDAP_BASE_DN=DC=shangpharma,DC=com
OLIGOLAB_LDAP_DOMAINS=CP.shangpharma.com,CD-GW.shangpharma.com,CE.shangpharma.com

# Auth
OLIGOLAB_JWT_SECRET=change-me-in-production
OLIGOLAB_AUTH_ENABLED=true

# PostgreSQL(独立库)
OLIGOLAB_PG_HOST=127.0.0.1
OLIGOLAB_PG_PORT=5434
OLIGOLAB_PG_DB=oligolab
OLIGOLAB_PG_USER=oligolab
OLIGOLAB_PG_PASSWORD=change-me
OLIGOLAB_PG_POOL_MIN=2
OLIGOLAB_PG_POOL_MAX=10

# CORS
OLIGOLAB_CORS_ORIGINS=https://oligolab.chempartner.com
EOF
```

- [ ] **Step 5: 创建 .env（从模板复制）**

```bash
cd /export/projects/sandbox/oligolab
cp .env.example .env
# 填写真实 PG 密码 / JWT_SECRET（实施时由用户/DBA 提供）
```

> 注意：`.env` 被 `.gitignore` 忽略，不会提交。

- [ ] **Step 6: 提交**

```bash
cd /export/projects/sandbox/oligolab
git add -A
git commit -m "chore: scaffold oligolab project (uv pyproject, gitignore, env template, dirs)"
```

---

### Task 2: 更新 spec 中确认的 pyproject 依赖（uv add）

**Files:**
- Modify: `/export/projects/sandbox/oligolab/pyproject.toml`

**Interfaces:**
- Consumes: Task 1 的 pyproject / venv
- Produces: 后端依赖已 `uv add`，`uv.lock` 生成，后续 Task 3 可直接 `uv run`/`uv sync`

- [ ] **Step 1: uv 添加后端运行依赖（安装到 .venv）**

```bash
cd /export/projects/sandbox/oligolab
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings asyncpg ldap3 "python-jose[cryptography]" gunicorn loguru python-multipart
```

期望：`uv.lock` 更新，依赖安装成功（退出码 0）。

- [ ] **Step 2: 提交**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add backend runtime deps via uv"
```

---

### Task 3: 后端 Config + 数据库层（pydantic-settings + asyncpg pool + 建表）

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

**Interfaces:**
- Consumes: `.env`（Task 1）, uv 依赖（Task 2）
- Produces:
  - `app.config.settings`：属性 `APP_NAME, APP_ENV, DEBUG, HOST, PORT, WORKERS, CORS_ORIGINS, AUTH_ENABLED, JWT_SECRET, LDAP_HOST, LDAP_PORT, LDAP_BASE_DN, LDAP_DOMAINS(list), PG_* , db 相关`
  - `app.database.init_db()` / `close_db()` / `execute_query(sql, params)->list[dict]` / `execute_one(sql, params)->dict|None` / `execute_insert(sql, params)`
  - `app.database.schema_init()`：幂等建表 `users` / `login_lockouts`
  - `make db-create`（Makefile 目标）：用 psql 创建独立库/用户

- [ ] **Step 1: 编写 config.py**

```python
"""OligoLab application configuration (pydantic-settings)."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "OligoLab"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 7130
    WORKERS: int = 4
    CORS_ORIGINS: str = "*"

    # LDAP 域账号
    LDAP_HOST: str = "10.1.1.56"
    LDAP_PORT: int = 389
    LDAP_BASE_DN: str = "DC=shangpharma,DC=com"
    LDAP_DOMAINS: str = "CP.shangpharma.com,CD-GW.shangpharma.com,CE.shangpharma.com"

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    AUTH_ENABLED: bool = True

    # PostgreSQL（独立库）
    PG_HOST: str = "127.0.0.1"
    PG_PORT: int = 5434
    PG_DB: str = "oligolab"
    PG_USER: str = "oligolab"
    PG_PASSWORD: str = ""
    PG_POOL_MIN: int = 2
    PG_POOL_MAX: int = 10

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def ldap_domain_list(self):
        return [d.strip() for d in self.LDAP_DOMAINS.split(",") if d.strip()]

    @property
    def pg_dsn(self) -> str:
        return f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = {"env_file": ".env", "env_prefix": "OLIGOLAB_"}


settings = Settings()
```

- [ ] **Step 2: 编写 database.py（asyncpg 池 + schema_init）**

```python
"""PostgreSQL connection pool + schema init (asyncpg, $1 params)."""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Sequence
import asyncpg
from loguru import logger
from app.config import settings

_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection):
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(
        host=settings.PG_HOST, port=settings.PG_PORT,
        database=settings.PG_DB, user=settings.PG_USER, password=settings.PG_PASSWORD,
        min_size=settings.PG_POOL_MIN, max_size=settings.PG_POOL_MAX,
        init=_init_connection,
    )
    await schema_init()
    logger.info(f"PostgreSQL pool ready | {settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}")


async def close_db():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_db() first")
    return _pool


async def execute_query(query, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
    async with _get_pool().acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


async def execute_one(query, params: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
    async with _get_pool().acquire() as conn:
        row = await conn.fetchrow(query, *params)
    return dict(row) if row else None


async def execute_insert(query, params: Sequence[Any] = ()):
    async with _get_pool().acquire() as conn:
        return await conn.execute(query, *params)


async def schema_init():
    """幂等建表。"""
    await execute_insert("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            display_name  TEXT NOT NULL DEFAULT '',
            department    TEXT NOT NULL DEFAULT '',
            email         TEXT NOT NULL DEFAULT '',
            auth_source   TEXT NOT NULL DEFAULT 'ldap',
            last_login_at TIMESTAMPTZ,
            login_count   INTEGER NOT NULL DEFAULT 0
        );
    """)
    await execute_insert("""
        CREATE TABLE IF NOT EXISTS login_lockouts (
            username        TEXT PRIMARY KEY,
            fail_count      INTEGER NOT NULL DEFAULT 0,
            locked_until    TIMESTAMPTZ,
            last_attempt_at TIMESTAMPTZ
        );
    """)
```

- [ ] **Step 3: 建独立库/用户（需 DBA 权限，先写 SQL 与 Makefile 目标）**

创建 `infra/db/create_oligolab_db.sql`：

```sql
-- 需以超级用户执行一次（实施时由用户/DBA 在 5434 上执行）
CREATE ROLE oligolab LOGIN PASSWORD 'change-me';
CREATE DATABASE oligolab OWNER oligolab;
```

在根 `Makefile` 添加（仅收集命令，由用户执行）：

```makefile
db-create:
	@echo "请以 pg 超管在 127.0.0.1:5434 执行 infra/db/create_oligolab_db.sql"
	@echo "示例: psql -h 127.0.0.1 -p 5434 -U postgres -f infra/db/create_oligolab_db.sql"
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat: add config and asyncpg db layer with schema init"
```

---

### Task 4: 域账号登录服务（LDAP + JWT + 锁定）

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth_service.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.database.execute_one/execute_insert`
- Produces:
  - `ldap_authenticator`（全局实例）
  - `await ldap_authenticator.authenticate(username, password) -> (bool, code:str, user_info:dict|None)`；user_info 可含 `attempts_left`/`locked_until`
  - `create_token(user_info: dict) -> str`
  - `verify_token(token: str) -> dict|None`
  - 锁定策略：3 次错锁 300s（`LOCKOUT_MAX=3`, `LOCKOUT_SECS=300`）
  - 首次登录自动 upsert `users`

- [ ] **Step 1: 编写 auth_service.py**

```python
"""LDAP 域账号认证 + JWT + 登录锁定（复用 complexa 方案）。"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException
from jose import jwt, JWTError

from app.config import settings
from app.database import execute_query, execute_one, execute_insert

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7
LOCKOUT_MAX = 3
LOCKOUT_SECS = 300


async def _check_lockout(username: str):
    row = await execute_one(
        "SELECT fail_count, locked_until FROM login_lockouts WHERE username = $1",
        (username,),
    )
    if not row:
        return False, 0, 0
    locked_until = row["locked_until"]
    if locked_until is not None:
        now = datetime.now(timezone.utc)
        if now < locked_until:
            return True, int((locked_until - now).total_seconds()), row["fail_count"]
    return False, 0, row["fail_count"]


async def _record_failure(username: str):
    now = datetime.now(timezone.utc)
    row = await execute_one(
        "SELECT fail_count, locked_until FROM login_lockouts WHERE username = $1", (username,)
    )
    if row:
        count = row["fail_count"]
        locked_until = row["locked_until"]
        if locked_until is not None and now >= locked_until:
            count = 0
        count += 1
        new_locked = now + timedelta(seconds=LOCKOUT_SECS) if count >= LOCKOUT_MAX else None
        await execute_insert(
            """UPDATE login_lockouts SET fail_count=$1, locked_until=$2, last_attempt_at=$3 WHERE username=$4""",
            (count, new_locked, now, username),
        )
    else:
        count = 1
        new_locked = now + timedelta(seconds=LOCKOUT_SECS) if count >= LOCKOUT_MAX else None
        await execute_insert(
            """INSERT INTO login_lockouts (username, fail_count, locked_until, last_attempt_at)
               VALUES ($1, $2, $3, $4)""",
            (username, count, new_locked, now),
        )
    if count >= LOCKOUT_MAX:
        return True, LOCKOUT_SECS, 0
    return False, 0, LOCKOUT_MAX - count


async def _record_success(username: str):
    await execute_insert("DELETE FROM login_lockouts WHERE username = $1", (username,))


async def _upsert_user(username: str, display: str, dept: str, email: str):
    now = datetime.now(timezone.utc)
    await execute_insert(
        """INSERT INTO users (username, display_name, department, email, auth_source, last_login_at, login_count)
           VALUES ($1,$2,$3,$4,'ldap',$5,1)
           ON CONFLICT (username) DO UPDATE SET
               display_name=EXCLUDED.display_name, department=EXCLUDED.department,
               email=EXCLUDED.email, last_login_at=EXCLUDED.last_login_at,
               login_count=users.login_count + 1""",
        (username, display, dept, email, now),
    )


class LDAPAuthenticator:
    def __init__(self):
        self.server_url = f"ldap://{settings.LDAP_HOST}:{settings.LDAP_PORT}"
        self.base_dn = settings.LDAP_BASE_DN
        self.domains = settings.ldap_domain_list or ["CP.shangpharma.com"]

    async def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        if not username or not password:
            return False, "AUTH_MISSING_CREDENTIALS", None
        ukey = username.strip().lower()

        is_locked, remaining, _ = await _check_lockout(ukey)
        if is_locked:
            return False, "USER_LOCKED", {"attempts_left": 0, "locked_until": time.time() + remaining}

        last_error = ""
        credential_error = False
        for domain in self.domains:
            success, error, user_info = self._try_bind(username, password, domain)
            if success:
                await _record_success(ukey)
                if user_info:
                    await _upsert_user(
                        user_info["username"], user_info["display_name"],
                        user_info["department"], user_info["email"],
                    )
                return True, "", user_info
            last_error = error
            if "invalidCredentials" in error or "Invalid credentials" in error.lower():
                credential_error = True
                break

        is_now_locked, lock_remaining, attempts_left = await _record_failure(ukey)
        meta = {"attempts_left": attempts_left}
        if is_now_locked:
            msg = "USER_LOCKED"
            meta["locked_until"] = time.time() + lock_remaining
        elif attempts_left == 1:
            msg = "WRONG_PASSWORD_LAST_ATTEMPT"
        else:
            msg = "WRONG_PASSWORD"
        logger.warning("LDAP auth failed for %s (locked=%s att_left=%s err=%s)",
                       username, is_now_locked, attempts_left, last_error)
        return False, msg, meta

    def _try_bind(self, username: str, password: str, domain: str) -> Tuple[bool, str, Optional[dict]]:
        user_dn = f"{username}@{domain}"
        try:
            server = Server(self.server_url, use_ssl=False, get_info=ALL)
            conn = Connection(server, user=user_dn, password=password,
                              authentication=SIMPLE, auto_bind=True)
            user_info = self._get_user_info(conn, username, domain)
            conn.unbind()
            return True, "", user_info
        except LDAPException as e:
            return False, str(e), None
        except Exception as e:
            return False, "AUTH_SERVICE_ERROR", None

    def _get_user_info(self, conn, username: str, domain: str) -> dict:
        info = {"username": username, "display_name": username,
                "department": "", "email": f"{username}@{domain}"}
        try:
            conn.search(search_base=self.base_dn,
                        search_filter=f"(sAMAccountName={username})",
                        search_scope=SUBTREE,
                        attributes=["cn", "mail", "displayName", "sAMAccountName", "department"])
            if conn.entries:
                e = conn.entries[0]
                if getattr(e, "displayName", None):
                    info["display_name"] = str(e.displayName)
                if getattr(e, "mail", None):
                    info["email"] = str(e.mail)
                if getattr(e, "department", None):
                    info["department"] = str(e.department)
        except Exception:
            pass
        return info


def create_token(user_info: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": user_info["username"],
        "display_name": user_info.get("display_name", ""),
        "department": user_info.get("department", ""),
        "email": user_info.get("email", ""),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


ldap_authenticator = LDAPAuthenticator()
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/
git commit -m "feat: add LDAP domain-auth service with JWT and lockout"
```

---

### Task 5: 认证路由 + JWT 中间件

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/middleware/auth.py`

**Interfaces:**
- Consumes: Task 4 `ldap_authenticator/create_token/verify_token`, `app.config.settings`
- Produces: `POST /api/auth/login`, `GET /api/auth/verify`, `POST /api/auth/logout`；`AuthMiddleware` 供 main.py 挂载。白名单路径常量 `AUTH_WHITELIST`。

- [ ] **Step 1: 编写 routers/auth.py**

```python
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.services.auth_service import ldap_authenticator, create_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    display_name: str
    department: str
    email: str


class LoginResponse(BaseModel):
    success: bool
    code: Optional[str] = None
    message: str
    token: Optional[str] = None
    user: Optional[UserInfo] = None
    attempts_left: Optional[int] = None
    locked_until: Optional[float] = None


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if not settings.AUTH_ENABLED:
        user_info = {"username": req.username, "display_name": req.username,
                     "department": "dev", "email": f"{req.username}@dev.local"}
        token = create_token(user_info)
        return LoginResponse(success=True, code="LOGIN_SUCCESS", message="Login successful",
                             token=token, user=UserInfo(**user_info))

    success, error, user_info = await ldap_authenticator.authenticate(req.username, req.password)
    if not success:
        resp = LoginResponse(success=False, code=error, message=error)
        if isinstance(user_info, dict):
            resp.attempts_left = user_info.get("attempts_left")
            resp.locked_until = user_info.get("locked_until")
        return resp

    token = create_token(user_info)
    return LoginResponse(success=True, code="LOGIN_SUCCESS", message="Login successful",
                         token=token, user=UserInfo(**user_info))


@router.get("/verify")
async def verify(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"authenticated": False}
    payload = verify_token(authorization.split(" ", 1)[1])
    if not payload:
        return {"authenticated": False}
    return {"authenticated": True,
            "user": {"username": payload.get("sub", ""),
                     "display_name": payload.get("display_name", ""),
                     "department": payload.get("department", ""),
                     "email": payload.get("email", "")}}


@router.post("/logout")
async def logout():
    return {"success": True, "code": "LOGOUT_SUCCESS", "message": "Logged out"}
```

- [ ] **Step 2: 编写 middleware/auth.py**

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.services.auth_service import verify_token

AUTH_WHITELIST = [
    "/api/auth/login", "/api/auth/logout", "/api/auth/verify",
    "/api/health", "/api/modules",
    "/docs", "/openapi.json", "/redoc",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        if not path.startswith("/api"):
            return await call_next(request)
        if not settings.AUTH_ENABLED or method == "OPTIONS":
            return await call_next(request)
        for w in AUTH_WHITELIST:
            if path.startswith(w):
                return await call_next(request)
        auth_header = request.headers.get("authorization", "")
        token = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else ""
        if not token:
            return JSONResponse(status_code=401, content={"detail": {"code": "AUTH_REQUIRED",
                "message": "Authentication required, please log in first"}})
        payload = verify_token(token)
        if not payload:
            return JSONResponse(status_code=401, content={"detail": {"code": "AUTH_EXPIRED",
                "message": "Authentication expired, please log in again"}})
        request.state.user = {"username": payload.get("sub", ""),
                              "display_name": payload.get("display_name", "")}
        return await call_next(request)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/routers/auth.py backend/app/middleware/
git commit -m "feat: add auth router and JWT middleware"
```

---

### Task 6: 模块数据 + health + main.py 入口

**Files:**
- Create: `backend/app/modules_data.py`
- Create: `backend/app/routers/modules.py`
- Create: `backend/app/routers/health.py`
- Create: `backend/app/main.py`

**Interfaces:**
- Consumes: Task 3 database, Task 5 AuthMiddleware
- Produces: `GET /api/health`; `GET /api/modules -> list[dict]`（模块列表）；`app.main:app`（FastAPI 实例，挂静态 `frontend/dist`、路由、中间件、lifespan 初始化/关闭数据库）

`modules_data.py` 定义 7 模块（前端与后端共用同一份内容）：

```python
MODULES = [
    {"slug": "seq-design", "name": "序列与修饰设计", "status": "规划中",
     "summary": "核酸序列设计、碱基/骨架/糖环修饰（2'-OMe、LNA、PS 等）设计工具。",
     "features": ["ASO/siRNA 序列设计", "化学修饰编辑", "修饰模式库", "序列导出"]},
    {"slug": "off-target", "name": "脱靶与靶点预测", "status": "规划中",
     "summary": "siRNA/ASO 脱靶预测、靶点筛选与特异性评估。",
     "features": ["脱靶打分", "靶点特异性评估", "同源比对"]},
    {"slug": "structure-properties", "name": "二级结构与理化性质", "status": "规划中",
     "summary": "MFE/二级结构、Tm、GC、分子量、溶解度、亲疏水等理化性质计算。",
     "features": ["二级结构预测", "热力学参数(MFE)", "理化性质计算"]},
    {"slug": "stability-immuno", "name": "稳定性与免疫原性", "status": "规划中",
     "summary": "核酸酶稳定性、半衰期、免疫原性/细胞因子风险预测。",
     "features": ["稳定性预测", "半衰期评估", "免疫原性风险"]},
    {"slug": "delivery", "name": "递送系统设计", "status": "规划中",
     "summary": "LNP / GalNAc / 配体偶联等递送系统设计与评估。",
     "features": ["LNP 配方设计", "GalNAc 偶联", "递送效率评估"]},
    {"slug": "project-data", "name": "项目与数据管理", "status": "规划中",
     "summary": "内部项目、序列、任务管理与实验数据台账。",
     "features": ["项目管理", "序列台账", "任务跟踪"]},
    {"slug": "literature", "name": "文献与知识库", "status": "规划中",
     "summary": "小核酸相关文献、专利与内部知识库检索。",
     "features": ["文献检索", "专利导航", "内部知识库"]},
]
```

- [ ] **Step 1: 编写 routers/health.py**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "app": "oligolab"}
```

- [ ] **Step 2: 编写 routers/modules.py**

```python
from fastapi import APIRouter
from app.modules_data import MODULES

router = APIRouter(prefix="/api", tags=["modules"])


@router.get("/modules")
async def list_modules():
    return {"modules": MODULES}
```

- [ ] **Step 3: 编写 main.py**

```python
"""OligoLab FastAPI entry point."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db, close_db
from app.middleware.auth import AuthMiddleware
from app.routers import auth, modules, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(CORSMiddleware,
                   allow_origins=settings.cors_origin_list,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])
app.add_middleware(AuthMiddleware)

app.include_router(auth.router)
app.include_router(modules.router)
app.include_router(health.router)

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
```

- [ ] **Step 4: 本地启动验证（开发模式 AUTH_ENABLED=false 且无 DB 时需先建库）**

```bash
cd /export/projects/sandbox/oligolab
# 先在 5434 上建库（见 Task 3）；或用临时 AUTH_ENABLED=false 且临时跳过 DB 验证前端
OLIGOLAB_AUTH_ENABLED=false uv run uvicorn app.main:app --app-dir backend --port 7130
```

> 实际验证需 `oligolab` 库存在。若库尚未建好，可先执行 Task 7（前端）后再统一联调。此处仅确认应用可导入、路由可注册。

- [ ] **Step 5: 提交**

```bash
git add backend/app/main.py backend/app/routers/backend/app/modules_data.py
git commit -m "feat: add main app, modules & health routes"
```

---

### Task 7: 前端脚手架（Vite + React + TS + 依赖）

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`

**Interfaces:**
- Consumes: 无（独立）
- Produces: 可 `npm run build` 的前端工程；`frontend/dist` 供 Task 6 托管。

- [ ] **Step 1: 创建前端文件**

`frontend/package.json`：

```json
{
  "name": "oligolab-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --port 5173 --host 0.0.0.0",
    "build": "tsc -b && vite build",
    "preview": "vite preview --port 5180 --host 0.0.0.0"
  },
  "dependencies": {
    "axios": "^1.7.9",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.2",
    "vite": "^6.0.5"
  }
}
```

`frontend/vite.config.ts`：

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:7130',
    },
  },
})
```

`frontend/tsconfig.json`：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

`frontend/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OligoLab · 小核酸药物研发平台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/src/main.tsx`：

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

- [ ] **Step 2: 安装依赖**

```bash
cd /export/projects/sandbox/oligolab/frontend
npm install
```

期望：`exit 0`，生成 `node_modules` 与 `package-lock.json`。

- [ ] **Step 3: 提交**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/main.tsx
git commit -m "chore: scaffold react+vite frontend"
```

---

### Task 8: 前端认证（auth utils + api client + Login 页 + 路由守卫）

**Files:**
- Create: `frontend/src/utils/auth.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

**Interfaces:**
- Consumes: 无（独立于后端，使用 `/api/auth/*`）
- Produces: `getToken/setToken/clearToken`, `getUser/setUser`, `isAuthenticated()`, `logout()`；`api`（axios 实例，自动注入 `Authorization: Bearer <token>`）；`Login` 页；`App` 路由与守卫（未登录访问 `/`、`/module/*` → 重定向 `/login`）

- [ ] **Step 1: 编写 utils/auth.ts**

```ts
const TOKEN_KEY = 'oligolab_token'
const USER_KEY = 'oligolab_user'

export interface AuthUser { username: string; display_name: string; department: string; email: string }

export function getToken(): string | null { return localStorage.getItem(TOKEN_KEY) }
export function setToken(token: string): void { localStorage.setItem(TOKEN_KEY, token) }
export function clearToken(): void { localStorage.removeItem(TOKEN_KEY) }

export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}
export function setUser(u: AuthUser): void { localStorage.setItem(USER_KEY, JSON.stringify(u)) }
export function clearUser(): void { localStorage.removeItem(USER_KEY) }

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const p = parts[1]
    return JSON.parse(atob(p.replace(/-/g, '+').replace(/_/g, '/')))
  } catch { return null }
}

export function isAuthenticated(): boolean {
  const token = getToken()
  if (!token) return false
  const payload = parseJwtPayload(token)
  if (!payload || !payload.exp) return false
  return Date.now() < (payload.exp as number) * 1000
}

export function logout(): void { clearToken(); clearUser() }
```

- [ ] **Step 2: 编写 api/client.ts**

```ts
import axios from 'axios'
import { getToken } from '../utils/auth'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
```

- [ ] **Step 3: 编写 App.tsx（路由 + 守卫）**

```tsx
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Home from './pages/Home'
import Module from './pages/Module'
import { isAuthenticated } from './utils/auth'

function RequireAuth({ children }: { children: JSX.Element }) {
  const location = useLocation()
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RequireAuth><Home /></RequireAuth>} />
      <Route path="/module/:slug" element={<RequireAuth><Module /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
```

- [ ] **Step 4: 编写 index.css（基础样式，登录页/首页共用）**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f7fb; color: #1f2937; }
a { text-decoration: none; color: inherit; }
```

- [ ] **Step 5: 编写 Login.tsx（域账号登录页）**

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dna, Eye, EyeOff, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import { isAuthenticated, setToken, setUser } from '../utils/auth'

interface LoginData { success: boolean; code?: string; message?: string; token?: string;
  user?: { username: string; display_name: string; department: string; email: string };
  attempts_left?: number; locked_until?: number }

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { if (isAuthenticated()) navigate('/', { replace: true }) }, [navigate])

  const fmtError = (d: LoginData): string => {
    if (d.code === 'USER_LOCKED' && d.locked_until) {
      const r = Math.max(0, Math.round((d.locked_until * 1000 - Date.now()) / 1000))
      return `账号已锁定，请 ${Math.floor(r / 60)}分${Math.floor(r % 60)}秒后重试`
    }
    if (d.code === 'WRONG_PASSWORD' && d.attempts_left != null) return `密码错误，还可尝试 ${d.attempts_left} 次`
    if (d.code === 'WRONG_PASSWORD_LAST_ATTEMPT') return '密码错误，仅剩最后 1 次机会'
    if (d.code === 'USER_LOCKED') return '账号已锁定，请稍后重试'
    if (d.code === 'AUTH_MISSING_CREDENTIALS') return '请输入工号和密码'
    return d.message && d.message !== d.code ? d.message : '登录失败，请检查工号和密码'
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) { setError('请输入工号和密码'); return }
    setLoading(true); setError('')
    try {
      const res = await api.post<LoginData>('/auth/login', { username: username.trim(), password })
      const data = res.data
      if (data.success && data.token) {
        setToken(data.token)
        if (data.user) setUser(data.user)
        navigate('/', { replace: true })
      } else {
        setError(fmtError(data))
      }
    } catch {
      setError('网络错误，无法连接服务器')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#0f172a,#1e3a8a)' }}>
      <form onSubmit={submit} style={{ width: 380, padding: 40, background: '#fff', borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center', marginBottom: 8 }}>
          <Dna color="#2563eb" size={30} />
          <h1 style={{ fontSize: 22 }}>OligoLab</h1>
        </div>
        <p style={{ textAlign: 'center', color: '#6b7280', marginBottom: 24 }}>小核酸药物研发平台 · 域账号登录</p>
        <input value={username} onChange={e => setUsername(e.target.value)} placeholder="工号（如 cp12398）"
          style={inp} autoFocus />
        <div style={{ position: 'relative' }}>
          <input type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
            placeholder="AD 域密码" style={inp} />
          <button type="button" onClick={() => setShow(!show)}
            style={{ position: 'absolute', right: 12, top: 12, background: 'none', border: 'none', cursor: 'pointer' }}>
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {error && <p style={{ color: '#dc2626', fontSize: 13, margin: '8px 0' }}>{error}</p>}
        <button type="submit" disabled={loading} style={{ width: '100%', padding: 12, marginTop: 16, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          {loading && <Loader2 size={16} className="spin" />} 登 录
        </button>
      </form>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin 1s linear infinite}`}</style>
    </div>
  )
}

const inp: React.CSSProperties = { width: '100%', padding: '12px 14px', margin: '8px 0', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14 }
```

- [ ] **Step 6: 构建验证**

```bash
cd /export/projects/sandbox/oligolab/frontend
npm run build
```

期望：`tsc` + `vite build` 成功，生成 `frontend/dist/`。

- [ ] **Step 7: 提交**

```bash
git add frontend/src
git commit -m "feat: add auth utils, axios client, login page, route guard"
```

---

### Task 9: 首页卡片 + 模块介绍页（新标签页）

**Files:**
- Create: `frontend/src/data/modules.ts`
- Create: `frontend/src/pages/Home.tsx`
- Create: `frontend/src/pages/Module.tsx`

**Interfaces:**
- Consumes: Task 8 路由；前端模块数据 `modules.ts`（与后端 `modules_data.MODULES` 内容一致）
- Produces: `/` 首页卡片网格，每卡片 `target=_blank` 打开 `/module/:slug`；`/module/:slug` 显示该模块文字介绍。

- [ ] **Step 1: 编写 data/modules.ts（与后端一致）**

```ts
export interface OligoModule {
  slug: string; name: string; status: string;
  summary: string; features: string[];
}
export const MODULES: OligoModule[] = [
  { slug: 'seq-design', name: '序列与修饰设计', status: '规划中',
    summary: '核酸序列设计、碱基/骨架/糖环修饰（2\'-OMe、LNA、PS 等）设计工具。',
    features: ['ASO/siRNA 序列设计', '化学修饰编辑', '修饰模式库', '序列导出'] },
  { slug: 'off-target', name: '脱靶与靶点预测', status: '规划中',
    summary: 'siRNA/ASO 脱靶预测、靶点筛选与特异性评估。',
    features: ['脱靶打分', '靶点特异性评估', '同源比对'] },
  { slug: 'structure-properties', name: '二级结构与理化性质', status: '规划中',
    summary: 'MFE/二级结构、Tm、GC、分子量、溶解度、亲疏水等理化性质计算。',
    features: ['二级结构预测', '热力学参数(MFE)', '理化性质计算'] },
  { slug: 'stability-immuno', name: '稳定性与免疫原性', status: '规划中',
    summary: '核酸酶稳定性、半衰期、免疫原性/细胞因子风险预测。',
    features: ['稳定性预测', '半衰期评估', '免疫原性风险'] },
  { slug: 'delivery', name: '递送系统设计', status: '规划中',
    summary: 'LNP / GalNAc / 配体偶联等递送系统设计与评估。',
    features: ['LNP 配方设计', 'GalNAc 偶联', '递送效率评估'] },
  { slug: 'project-data', name: '项目与数据管理', status: '规划中',
    summary: '内部项目、序列、任务管理与实验数据台账。',
    features: ['项目管理', '序列台账', '任务跟踪'] },
  { slug: 'literature', name: '文献与知识库', status: '规划中',
    summary: '小核酸相关文献、专利与内部知识库检索。',
    features: ['文献检索', '专利导航', '内部知识库'] },
]
```

- [ ] **Step 2: 编写 Home.tsx（卡片网格，target=_blank）**

```tsx
import { useNavigate } from 'react-router-dom'
import { logout } from '../utils/auth'
import { MODULES } from '../data/modules'

const iconColor = ['#2563eb', '#7c3aed', '#0d9488', '#dc2626', '#ea580c', '#059669', '#0284c7']

export default function Home() {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', padding: '40px 48px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: '#2563eb', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700 }}>O</div>
          <div>
            <h1 style={{ fontSize: 24 }}>OligoLab · 小核酸药物研发平台</h1>
            <p style={{ color: '#6b7280', fontSize: 14 }}>公司内网 SaaS · 点击卡片在新标签页查看模块介绍</p>
          </div>
        </div>
        <button onClick={() => { logout(); navigate('/login', { replace: true }) }}
          style={{ padding: '8px 18px', border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', cursor: 'pointer' }}>
          退出登录
        </button>
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 24 }}>
        {MODULES.map((m, i) => (
          <a key={m.slug} href={`/module/${m.slug}`} target="_blank" rel="noopener noreferrer"
            style={{ background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #e5e7eb',
              boxShadow: '0 4px 16px rgba(0,0,0,.04)', display: 'flex', flexDirection: 'column', gap: 14,
              transition: 'transform .15s, box-shadow .15s' }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 12px 28px rgba(0,0,0,.1)' }}
            onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,.04)' }}>
            <div style={{ width: 46, height: 46, borderRadius: 12, background: `${iconColor[i % iconColor.length]}16`,
              color: iconColor[i % iconColor.length], display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 20 }}>
              {String(i + 1).padStart(2, '0')}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <h3 style={{ fontSize: 18 }}>{m.name}</h3>
                <span style={{ fontSize: 12, color: '#b45309', background: '#fef3c7', padding: '2px 8px', borderRadius: 10 }}>{m.status}</span>
              </div>
              <p style={{ color: '#6b7280', fontSize: 14, lineHeight: 1.6 }}>{m.summary}</p>
            </div>
            <span style={{ color: '#2563eb', fontSize: 13 }}>点击查看 →</span>
          </a>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 编写 Module.tsx（单模块介绍页）**

```tsx
import { Navigate, useParams } from 'react-router-dom'
import { MODULES } from '../data/modules'

export default function Module() {
  const { slug } = useParams()
  const m = MODULES.find(x => x.slug === slug)
  if (!m) return <Navigate to="/" replace />
  return (
    <div style={{ minHeight: '100vh', padding: '48px 56px', maxWidth: 880, margin: '0 auto' }}>
      <a href="/" style={{ color: '#2563eb' }}>← 返回首页</a>
      <div style={{ marginTop: 20, background: '#fff', borderRadius: 16, padding: 40, border: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <h1 style={{ fontSize: 28 }}>{m.name}</h1>
          <span style={{ fontSize: 13, color: '#b45309', background: '#fef3c7', padding: '3px 10px', borderRadius: 12 }}>{m.status}</span>
        </div>
        <p style={{ color: '#4b5563', fontSize: 16, lineHeight: 1.8, marginBottom: 24 }}>{m.summary}</p>
        <h3 style={{ marginBottom: 12, color: '#111827' }}>功能规划</h3>
        <ul style={{ paddingLeft: 22, lineHeight: 2, color: '#374151' }}>
          {m.features.map(f => <li key={f}>{f}</li>)}
        </ul>
        <p style={{ marginTop: 24, color: '#9ca3af', fontSize: 13 }}>当前为占位页面，具体功能开发中，敬请期待。</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 构建验证**

```bash
cd /export/projects/sandbox/oligolab/frontend
npm run build
```

期望：`npm run build` 成功。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/Home.tsx frontend/src/pages/Module.tsx frontend/src/data/modules.ts
git commit -m "feat: add card home page and module detail pages"
```

---

### Task 10: 部署脚本（gunicorn 多 worker + systemd）

**Files:**
- Create: `backend/run_prod.sh`
- Create: `backend/run_dev.sh`
- Create: `infra/systemd/oligolab.service`

**Interfaces:**
- Consumes: Task 1-6 后端, Task 7-9 前端 dist
- Produces: 生产/开发启动脚本；`oligolab.service` systemd 单元（root 安装）。

- [ ] **Step 1: 编写 run_dev.sh**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"
export OLIGOLAB_APP_ENV=development
export OLIGOLAB_DEBUG=true
exec uv run uvicorn app.main:app --app-dir .. --host "${OLIGOLAB_HOST:-127.0.0.1}" --port "${OLIGOLAB_PORT:-7130}" --reload
```

- [ ] **Step 2: 编写 run_prod.sh（gunicorn 多 worker）**

```bash
#!/bin/bash
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
```

- [ ] **Step 3: 编写 systemd 单元**

```ini
[Unit]
Description=OligoLab 小核酸药物研发平台 (FastAPI)
After=network.target postgresql.service

[Service]
Type=simple
User=aiuser
Group=aiuser
WorkingDirectory=/export/projects/sandbox/oligolab
EnvironmentFile=/export/projects/sandbox/oligolab/.env
ExecStart=/export/projects/sandbox/oligolab/.venv/bin/uvicorn app.main:app --app-dir /export/projects/sandbox/oligolab/backend --host 127.0.0.1 --port 7130 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> 说明：systemd 单元里直接调用 `.venv/bin/uvicorn`（多 worker 用 uvicorn 原生 `--workers`，与 complexa 一致）；若坚持 gunicorn 二进制，将 ExecStart 改为 `ExecStart=/export/projects/sandbox/oligolab/.venv/bin/gunicorn app.main:app --chdir /export/projects/sandbox/oligolab/backend --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:7130`。二者都满足“多 worker”。

- [ ] **Step 4: 提交**

```bash
git add backend/run_prod.sh backend/run_dev.sh infra/systemd/oligolab.service
git commit -m "feat: add prod/dev run scripts and systemd unit"
```

---

### Task 11: nginx + 部署上线

**Files:**
- Create: `infra/nginx/oligolab-chempartner.conf`
- (部署时) 复制到 `/etc/nginx/conf.d/`，需 root

**Interfaces:**
- Consumes: 生产服务跑在 7130（Task 10）
- Produces: `oligolab.chempartner.com` 反代到 127.0.0.1:7130；443 用现有泛域名证书。

- [ ] **Step 1: 编写 nginx 站点配置**

```nginx
# OligoLab - oligolab.chempartner.com -> 127.0.0.1:7130
server {
    listen 80;
    server_name oligolab.chempartner.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name oligolab.chempartner.com;

    ssl_certificate /etc/nginx/ssl/chempartner.com.fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/chempartner.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:7130;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 600s;
    }
}
```

- [ ] **Step 2: 部署操作（需 root，执行用户：root）**

```bash
# 1) root：复制 nginx 配置
sudo cp /export/projects/sandbox/oligolab/infra/nginx/oligolab-chempartner.conf /etc/nginx/conf.d/
sudo nginx -t
#   期望: syntax is ok

# 2) root：创建独立 Postgres 库（见 Task 3 的 SQL，先在 5434 建库）
# 3) root：安装 systemd 服务并启动
sudo cp /export/projects/sandbox/oligolab/infra/systemd/oligolab.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oligolab
systemctl status oligolab --no-pager

# 4) 若第一步 nginx -t 通过，reload
sudo systemctl reload nginx
```

- [ ] **Step 3: 端到端验证**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://oligolab.chempartner.com/           # 期望 200（或跳登录）
curl -s https://oligolab.chempartner.com/api/health                                  # 期望 {"status":"ok","app":"oligolab"}
curl -s -X POST https://oligolab.chempartner.com/api/auth/login -H 'Content-Type: application/json' \
    -d '{"username":"测试或停用工号","password":"x"}'                                  # 期望错误码(WRONG_PASSWORD 或 USER_LOCKED)
```

- [ ] **Step 4: 提交**

```bash
git add infra/nginx/oligolab-chempartner.conf
git commit -m "feat: add nginx site config for oligolab.chempartner.com"
```

---

## Self-Review

**1. Spec coverage:**
- 前端卡片+新标签页介绍页 → Task 9 ✓
- 域账号登录(LDAP+JWT) → Task 4/5/8 ✓
- Postgres 5434 独立库 → Task 3(建库SQL+asyncpg) ✓
- gunicorn 多 worker → Task 10 ✓
- uv + 较新依赖 → Task 1/2 ✓
- nginx → Task 11 ✓
- systemd 保活 → Task 10/11 ✓
- 7 模块 → Task 6/9 ✓

**2. Placeholder scan:** 无 TBD/TODO；所有代码步骤含完整代码。建库 SQL 的密码用 `change-me` 占位，实施时由用户/DBA 填写（已在 Global Constraints 与 Task 3 注明）。

**3. Type consistency:** `MODULES` 结构 (slug/name/status/summary/features) 前后端一致；`create_token/verify_token/ldap_authenticator.authenticate` 签名在 Task 4/5 一致；`execute_query/execute_one/execute_insert` 在 Task 3/4 一致；前端 `setToken/setUser/isAuthenticated/logout/logout` 命名一致。
