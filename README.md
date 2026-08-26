# OligoLab · 小核酸药物研发平台

公司**内网 SaaS**：小核酸（oligonucleotide）药物研发一体化平台。MVP 提供卡片式首页（每卡片新标签页打开模块文字介绍页）+ 公司域账号登录。

- 域名：`https://oligolab.chempartner.com` → nginx → `127.0.0.1:7130`
- 前端：React 18 + Vite + TypeScript（`frontend/`）
- 后端：Python 3.11 (uv) + FastAPI（`backend/`）
- 数据库：公司 Postgres `127.0.0.1:5434` 的独立库 `oligolab`
- 认证：LDAP 公司域账号（UPN 绑定）+ JWT

## 快速开始

### 后端
```bash
uv sync                    # 安装依赖（Python 3.11 venv）
cp .env.example .env       # 填写真实配置
./backend/run_dev.sh       # 开发模式（热重载）
```

### 前端
```bash
cd frontend && npm install && npm run build
```

### 生产
```bash
./backend/run_prod.sh      # gunicorn 多 worker，端口 7130
```
详见 `docs/superpowers/specs/2026-08-26-oligolab-saas-design.md` 设计文档。
