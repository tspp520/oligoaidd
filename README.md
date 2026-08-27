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

## 模块：脱靶与靶点预测（off-target）✅ 已上线（内网验证版）

基于 [OligoFormer](https://github.com/lulab/OligoFormer)（清华 lulab，transformer + RNA-FM）搭建的
独立内网 SaaS，提供 **siRNA 功效预测 / 脱靶(PITA+TargetScan) / 毒性筛选**，挂载在
`https://oligolab.chempartner.com/offtarget/`（服务端口 `127.0.0.1:7131`）。

- 代码：`tools/off-target/`（含 OligoFormer 源码、PerlLib、独立 SaaS 服务）
- 文档：`docs/technical/2026-08-26-ooftarget-design.md`（设计）、`...-deployment.md`（部署）、`...-pitfalls.md`（踩坑）
- ⚠️ 授权：OligoFormer 学术/非商业免费，**商业使用需清华授权**。
