# OligoLab 小核酸药物内网 SaaS — 设计文档

- 日期：2026-08-26
- 状态：已批准（域名: oligolab.chempartner.com 反代到本机端口 7130）
- 项目路径：`/export/projects/sandbox/oligolab/`
- 复用参考：`/export/projects/sandbox/orion_sandbox/complexa/complexa-prod/`（域账号登录、FastAPI 结构、部署脚本）

## 1. 目标

为公司内部搭建一套「小核酸（oligonucleotide）药物研发」内网 SaaS。本期为 **MVP**：
卡片式首页，每个模块以卡片呈现，点击卡片**新开浏览器标签页**展示该模块的文字介绍页（标题、简介、功能规划、当前状态）。平台带**公司域账号登录**。后续再逐个模块接入真实功能。

## 2. 已确认的决策

| 决策项 | 结论 |
|---|---|
| 端口 | `7130`（用户选定，已确认本机空闲无监听） |
| 前端 | React 18 + Vite + TypeScript（与 complexa 一致） |
| 后端 | Python FastAPI（`uv` 管理 venv，用兼容性好的较新版本） |
| Python 环境 | `uv` 在项目下建 `.venv`，`uv` 管理依赖 |
| 数据库 | 公司 Postgres `127.0.0.1:5434`（**新建独立库，不写 complexa 的 bioarch 库**） |
| 运行方式 | gunicorn + UvicornWorker 多 worker（比照 complexa 的多 worker 部署） |
| 认证 | 复用 complexa 的 LDAP 公司域账号登录 + JWT |
| 域名 | `oligolab.chempartner.com` → nginx → 127.0.0.1:7130 |

## 3. 总体架构

```
用户浏览器
   │  https://oligolab.chempartner.com
   ▼
NGINX (80 → 301, 443 ssl 泛域名证书)
   │ proxy_pass
   ▼
FastAPI (gunicorn uvicorn workers, 127.0.0.1:7130)
   ├── /           托管 React 前端构建产物 (frontend/dist)
   ├── /api/auth/* 登录/校验/登出 (LDAP + JWT)
   ├── /api/modules 模块列表（首页动态读取）
   └── /api/health 健康检查
   ▼
公司 AD 域 (LDAP *.shangpharma.com, 10.1.1.56:389)
公司 Postgres (127.0.0.1:5434, oligolab 独立库)
```

单进程部署：FastAPI 同时托管前端静态文件和 `/api`，nginx 只需反代一个端口 `7130`。卡片新标签页用前端路由 `/module/:slug` + `target=_blank` 实现。

## 4. 目录结构

```
oligolab/
├── pyproject.toml            # uv 管理后端依赖
├── uv.lock
├── .env.example              # 环境变量模板（含 LDAP / PG / JWT）
├── .env                      # 本地/生产实际配置（不提交）
├── backend/
│   ├── app/
│   │   ├── config.py         # pydantic-settings（PG/LDAP/JWT/端口）
│   │   ├── main.py           # FastAPI 入口，挂静态、路由、中间件
│   │   ├── database.py       # asyncpg 连接池 + init_db
│   │   ├── middleware/auth.py# JWT 认证中间件（保护 /api/*）
│   │   ├── routers/
│   │   │   ├── auth.py       # /api/auth/login|verify|logout
│   │   │   ├── modules.py    # /api/modules 模块列表
│   │   │   └── health.py     # /api/health
│   │   └── services/
│   │       └── auth_service.py # LDAP 认证 + JWT + 锁定
│   ├── requirements.txt      # uv sync 使用的锁定清单（供参考/回溯）
│   ├── run_prod.sh           # gunicorn 多 worker 生产启动
│   └── run_dev.sh            # uvicorn --reload 开发启动
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx           # 路由 + 守卫
│       ├── api/client.ts     # axios 实例（带 token 注入）
│       ├── utils/auth.ts     # token/user 存取 + isAuthenticated
│       ├── pages/Login.tsx   # 域账号登录页
│       ├── pages/Home.tsx    # 卡片式首页
│       └── pages/Module.tsx  # 单个模块介绍页（新标签页打开）
├── docs/superpowers/specs/2026-08-26-oligolab-saas-design.md  # 本文档
└── infra/
    └── nginx/oligolab-chempartner.conf   # nginx 站点配置（部署时复制到 /etc/nginx/conf.d/）
```

## 5. 技术栈与版本策略

- **Python**：`uv` 建 venv，`uv python pin 3.11`（新且兼容性好的稳定版），依赖用 `uv add` 安装**最新的稳定版本**（fastapi、uvicorn[standard]、pydantic、pydantic-settings、asyncpg、ldap3、python-jose[cryptography]、loguru、gunicorn、python-multipart）。
- **前端**：React 18 + Vite + TypeScript, axios、react-router-dom、lucide-react。与 complexa 前端风格一致（方便维护）。

## 6. 数据库（公司 Postgres 5434，oligolab 独立库）

> 不读写 complexa 的 `bioarch` 库。需在 5434 实例上创建独立库/用户：`oligolab`。

表结构（MVP）：
- `users`：LDAP 首次登录自动注册。列：`username`(PK)、`display_name`、`department`、`email`、`auth_source`、`last_login_at`、`login_count`。
- `login_lockouts`：`username`(PK)、`fail_count`、`locked_until`、`last_attempt_at`。
- `modules`（可选，备选）：模块元信息；MVP 优先用前端静态配置，后端 `modules.py` 返回同一份数据即可。

连接：`asyncpg` 连接池（host 127.0.0.1, port 5434, db/user 独立），`$1` 位置参数风格，与 complexa 一致。`init_db()` 在应用启动时建池并建表（幂等 `CREATE TABLE IF NOT EXISTS`）。

## 7. 域账号登录模块（复用 complexa 方案）

后端 `services/auth_service.py`：
- **LDAP UPN 绑定**：`ldap3` 依次尝试 `CP.shangpharma.com` / `CD-GW.shangpharma.com` / `CE.shangpharma.com`（host `10.1.1.56:389`，`BASE_DN=DC=shangpharma,DC=com`，均取自 `.env` 可覆盖）。`_try_bind` 为阻塞 I/O，放在线程中执行。
- **JWT**：`python-jose` 签发（`HS256`，7 天有效期），payload 含 sub/display_name/department/email。
- **锁定策略**：连续错误 3 次锁定 300 秒（存 `login_lockouts`）；成功清除；失败返回 `attempts_left`/`locked_until`。
- **自动注册**：登录成功将用户 upsert 进 `users` 表。
- **AUTH_ENABLED 开关**：`config.AUTH_ENABLED=False` 时放行（开发调试）。生产默认 `True`。

路由 `routers/auth.py`：
- `POST /api/auth/login`（username=工号, password=AD 域密码）
- `GET /api/auth/verify`
- `POST /api/auth/logout`

中间件 `middleware/auth.py`：保护 `/api/*`，白名单放行 `login/verify/logout/health/docs/openapi.json/redoc`；`OPTIONS` 放行；校验 `Authorization: Bearer <jwt>`，有效则写入 `request.state.user`。

前端：
- `pages/Login.tsx`：工号 + AD 密码表单，错误提示（含锁定剩余时间、剩余尝试次数），登录成功存 token 跳首页；已登录自动跳转。
- `utils/auth.ts`：token/user 的 localStorage 存取、`isAuthenticated()`（解析 JWT exp）、`logout()`。
- `App.tsx`：`/`（首页，需登录）、`/login`、`/module/:slug`；未登录访问受保护路由跳 `/login`。

## 8. 首页卡片与模块（7 个）

卡片式首页，每张卡片点击后 `target=_blank` 新开 `/module/:slug`。每模块介绍页含：标题、简介、功能规划、当前状态（占位/规划/建设中）。

| # | slug | 模块 | 当前状态 |
|---|---|---|---|
| 1 | seq-design | 序列与修饰设计 | 规划中 |
| 2 | off-target | 脱靶与靶点预测 | 规划中 |
| 3 | structure-properties | 二级结构与理化性质 | 规划中 |
| 4 | stability-immuno | 稳定性与免疫原性 | 规划中 |
| 5 | delivery | 递送系统设计 | 规划中 |
| 6 | project-data | 项目与数据管理 | 规划中 |
| 7 | literature | 文献与知识库 | 规划中 |

模块数据以一份静态配置（前端 `src/data/modules.ts` + 后端 `/api/modules` 返回同一内容）维护，便于后续动态扩展。

## 9. nginx

新建站点配置 `infra/nginx/oligolab-chempartner.conf`（部署时复制到 `/etc/nginx/conf.d/`）：
- `listen 80; server_name oligolab.chempartner.com;` → `return 301 https://$host$request_uri;`
- `listen 443 ssl http2;` 使用现有泛域名证书 `/etc/nginx/ssl/chempartner.com.fullchain.pem` + `.key`。
- `location / { proxy_pass http://127.0.0.1:7130; ... }`（带 WebSocket/Upgrade、X-Forwarded-* 头、超时）。

作用：让 `oligolab.chempartner.com` 不再落到旧的 AdmetX/默认站点，而是指向本新平台。需 root 执行 `nginx -t && systemctl reload nginx`。

## 10. 部署与运行

- **后端**：`uv` 建 `.venv`（Python 3.11）→ `uv sync` 安装依赖。
- **前端**：`npm install` → `npm run build` 产出 `frontend/dist`。
- **生产启动**：`backend/run_prod.sh` 用 `gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:7130 app.main:app`（多 worker，比照 complexa）。
- **systemd 保活**：注册 `oligolab.service`，ExecStart 指向 run_prod.sh；`Restart=always`。
- **nginx**：复制站点配置，`nginx -t && systemctl reload nginx`。

## 11. 安全与合规

- 内网域名 `*.chempartner.com` 暴露，访问受登录（LDAP + JWT）保护。
- `.env` 含 LDAP/JWT/PG 敏感配置，不提交到版本库（提供 `.env.example` 模板）。
- 不在日志中输出明文密码；LDAP 密码仅用于绑定，不做持久化。
- 不跨项目读取/复制 complexa 数据；oligolab 使用独立 Postgres 库。

## 12. 本期不做（YAGNI）

- 不做各模块真实计算功能（仅文字介绍页）。
- 不做北森 HR 姓名同步、GPU 调度、配额、审计日志（complexa 有，但本 MVP 不需要）。
- 不做 SSO 单点对接（沿用 LDAP 账号密码登录即可）。
