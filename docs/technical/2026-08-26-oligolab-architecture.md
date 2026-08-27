# OligoLab 技术架构与数据库设计

- 日期：2026-08-26
- 状态：MVP 已实现并部署（`https://oligolab.chempartner.com` → `127.0.0.1:7130`）
- 相关文档：
  - 产品/总设计：[`../superpowers/specs/2026-08-26-oligolab-saas-design.md`](../superpowers/specs/2026-08-26-oligolab-saas-design.md)
  - 实施计划：[`../superpowers/plans/2026-08-26-oligolab-saas.md`](../superpowers/plans/2026-08-26-oligolab-saas.md)
  - 踩坑记录：[`2026-08-26-oligolab-pitfalls.md`](./2026-08-26-oligolab-pitfalls.md)

---

## 1. 总体架构

```
用户浏览器
   │  https://oligolab.chempartner.com
   ▼
NGINX (80→301, 443 ssl 泛域名证书) —— /etc/nginx/conf.d/oligolab-chempartner.conf
   │ proxy_pass
   ▼
FastAPI (gunicorn/uvicorn 多 worker, 127.0.0.1:7130) —— backend/
   ├── /            托管 React 前端构建产物 (frontend/dist)
   ├── /api/auth/*  LDAP 域账号登录 + JWT（login/verify/logout）
   ├── /api/modules  模块列表
   └── /api/health   健康检查
   ▼
公司 AD 域 (LDAP: *.shangpharma.com, 10.1.1.56:389)
公司 Postgres (127.0.0.1:5434, 独立库 oligolab)
```

单进程部署：FastAPI 同时托管前端静态文件与 `/api`，nginx 只需反代一个端口 7130。

## 2. 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 后端 | Python + FastAPI（uv 管理 venv，Python 3.11） | fastapi **0.115.6**（锁定）、uvicorn 0.52、pydantic 2.13 |
| 数据库驱动 | asyncpg（连接池，`$1` 参数风格） | 0.31.0 |
| LDAP | ldap3（UPN 绑定） | 2.9.1 |
| JWT | python-jose[cryptography] | 3.5.0 |
| 前端 | React 18 + Vite + TypeScript | vite 6、react 18.3 |
| 前端库 | axios、react-router-dom、lucide-react | — |
| 部署 | gunicorn / uvicorn `--workers 4` + systemd + nginx | — |

关键点：**FastAPI 锁 0.115.6**，不升 0.141（后者的 starlette 1.6 有 `include_router` 不注册路由的 bug，详见踩坑文档）。

## 3. 数据库（公司 Postgres 5434，独立库）

### 3.1 实例与连接信息

- 实例：`molcraft-postgres` Docker 容器（postgres:16-alpine），映射 `0.0.0.0:5434→容器内5432`
- 数据目录（宿主 bind）：`/home/aiuser/data/molcraft-pg`
- 连接（对应 `.env`，`OLIGOLAB_` 前缀）：
  - Host：`127.0.0.1`，Port：`5434`
  - Database：`oligolab`，User：`oligolab`
  - Password：见 `/export/projects/sandbox/oligolab/.env` 的 `OLIGOLAB_PG_PASSWORD`
  - 池：min 2 / max 10
- 连接串示例：`postgresql://oligolab:<密码>@127.0.0.1:5434/oligolab`
- 该容器内**没有 `postgres` 角色**；超级用户 `molcraft` 被设成 `NOLOGIN`；可登录的超级用户是 **`bioarch`**（建库当初正是用它创建的 oligolab，见踩坑文档）。

### 3.2 表结构（`schema_init()` 幂等建表）

```sql
-- 用户表：LDAP 首次登录自动注册
CREATE TABLE users (
    username      TEXT PRIMARY KEY,          -- 工号，如 cp12398
    display_name  TEXT NOT NULL DEFAULT '',
    department    TEXT NOT NULL DEFAULT '',
    email         TEXT NOT NULL DEFAULT '',
    auth_source   TEXT NOT NULL DEFAULT 'ldap',
    last_login_at TIMESTAMPTZ,
    login_count   INTEGER NOT NULL DEFAULT 0
);

-- 登录锁定表：连续错 3 次锁 300 秒
CREATE TABLE login_lockouts (
    username        TEXT PRIMARY KEY,
    fail_count      INTEGER NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    last_attempt_at TIMESTAMPTZ
);
```

### 3.3 访问层

`backend/app/database.py`：
- `init_db()`：创建 asyncpg 连接池 + `schema_init()` 建表
- `close_db()`：关闭池
- `execute_query(sql, params) -> list[dict]`
- `execute_one(sql, params) -> dict | None`
- `execute_insert(sql, params)`
- 约定：所有 SQL 用 `$1, $2, ...` 位置参数（asyncpg 风格）；json/jsonb 已注册编解码

## 4. 域账号认证（复用 complexa 方案）

`backend/app/services/auth_service.py`：
- **LDAP UPN 绑定**：依次尝试 `CP/CD-GW/CE.shangpharma.com`（host `10.1.1.56:389`，`BASE_DN=DC=shangpharma,DC=com`），均为 `.env` 可覆盖
- **JWT**：HS256，7 天有效期，`payload.exp/iat` 用**epoch 时间戳**（float）
- **锁定**：连续 3 次错误锁 300s（存 `login_lockouts`）；成功清除
- **自动注册**：登录成功 upsert 进 `users` 表
- `AUTH_ENABLED` 开关：关闭时放行（开发调试），生产默认 `True`

`backend/app/middleware/auth.py`：保护 `/api/*`，白名单放行 `login/verify/logout/health/modules/docs/openapi.json/redoc` 及 `OPTIONS`；有效 JWT 写入 `request.state.user`。

`backend/app/routers/auth.py`：
- `POST /api/auth/login`（username=工号，password=AD 域密码）
- `GET  /api/auth/verify`
- `POST /api/auth/logout`

## 5. 前端与模块

`frontend/`：React 18 + Vite + TS。
- `src/utils/auth.ts`：token/user 的 localStorage 存取、`isAuthenticated()`（校验 JWT exp）
- `src/api/client.ts`：axios 实例，自动注入 `Authorization: Bearer <token>`
- `src/pages/Login.tsx`：域账号登录页（错误提示含锁定剩余时间/剩余次数）
- `src/pages/Home.tsx`：卡片式首页，每卡片 `target=_blank` 打开 `/module/:slug`
- `src/pages/Module.tsx`：单模块介绍页（标题/简介/功能规划/状态）
- `src/data/modules.ts`：7 模块静态数据（与后端 `backend/app/modules_data.py` 一致）

### 5.1 路由
| 路径 | 页面 | 说明 |
|---|---|---|
| `/login` | Login | 未登录访问受保护页会跳到这 |
| `/` | Home | 卡片首页（需登录） |
| `/module/:slug` | Module | 模块介绍页（新标签页，需登录） |

### 5.2 7 个模块
序/脱靶与靶点/二级结构与理化性质/稳定性与免疫原性/递送系统/项目与数据管理/文献与知识库。
其中 **脱靶与靶点预测（off-target）** 已接入真实功能（OligoFormer 内网 SaaS，挂载于 `/offtarget/`），
其余仍为"规划中"介绍页。off-target 详细设计/部署/踩坑见：
`docs/technical/2026-08-26-ooftarget-{design,deployment,pitfalls}.md`。

## 6. 部署

- 后端：`backend/run_prod.sh`（`gunicorn --chdir backend --workers 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:7130`）
- systemd：`infra/systemd/oligolab.service`（`EnvironmentFile=.env`，`uvicorn ... --workers 4`）
- nginx：`infra/nginx/oligolab-chempartner.conf`（80→301；443 ssl 用泛域名证书 `chempartner.com.fullchain.pem`；反代 `127.0.0.1:7130`）
- 建库：`infra/db/create_oligolab_db.sql` + `reset_and_create_oligolab.sh`

## 7. 安全与注意

- `.env` 含敏感配置（JWT_SECRET / PG 密码），已被 `.gitignore` 忽略，**不提交**；提供 `.env.example` 模板
- 日志/文档不输出完整密码明文
- `oligolab` 使用独立库，**不读不写 complexa 的 bioarch 库**
- 重启/部署需 root：`systemctl restart oligolab`、`nginx -t && systemctl reload nginx`
