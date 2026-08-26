# OligoLab 部署踩坑记录

- 日期：2026-08-26
- 目的：记录从开发到上线遇到的所有问题、根因与解决办法，方便日后复现/运维
- 相关文档：
  - 架构与数据库：[`2026-08-26-oligolab-architecture.md`](./2026-08-26-oligolab-architecture.md)
  - 产品/总设计：[`../superpowers/specs/2026-08-26-oligolab-saas-design.md`](../superpowers/specs/2026-08-26-oligolab-saas-design.md)
  - 实施计划：[`../superpowers/plans/2026-08-26-oligolab-saas.md`](../superpowers/plans/2026-08-26-oligolab-saas.md)

---

## 坑 1：FastAPI 最新版 0.141.1 的 `include_router` 不注册路由

**现象**：用 `uv add fastapi`（拉到当时最新 0.141.1 + starlette 1.6.0）后，`app.include_router(auth.router)` 只往路由表里加了一个 `path=None` 的空条目，`/api/*` 路由全部缺失，接口 404。

**根因**：fastapi 0.141.1 与 starlette 1.6.0 的兼容 bug（`include_router` 复制 APIRoute 时出错）。

**解决**：锁到生产验证过的 `fastapi==0.115.6`（对应 starlette 0.41.3），立即恢复正常。验证：
```python
from fastapi import APIRouter, FastAPI
r = APIRouter(prefix='/x'); @r.get('/hello'); ...
# include 后应能看到 /x/hello
```
→ 结论：**本项目 FastAPI 用 0.115.6，勿升 0.141**。

## 坑 2：`uv init --package=false` 语法报错

**现象**：`uv init --package=false --name oligolab` 报 `error: unexpected value 'false' for '--package'`。

**解决**：该版本不支持 `--package=false` 写法。直接手写 `pyproject.toml`（`requires-python >=3.11`），再 `uv python pin 3.11` + `uv add` 装依赖即可。

## 坑 3：本机域名 `oligolab.chempartner.com` 跳到 AdmetX 平台

**现象**：浏览器访问 `oligolab.chempartner.com` 显示"睿智医药 AdmetX 成药性预测平台"。

**根因**：**不是 nginx 配置错误**，而是 `oligolab-chempartner.conf` 根本没装进 `/etc/nginx/conf.d/`。没有 vhost 匹配该域名时，nginx 会落到"监听该端口的**第一个 server 块**"作默认 —— `conf.d` 字母序第一个正是 `admetx-chempartner.conf`，所以被 AdmetX 默认块承接代理到 3030。

**解决**：把 `infra/nginx/oligolab-chempartner.conf` 复制到 `/etc/nginx/conf.d/` + `nginx -t` + `systemctl reload nginx`，让 `oligolab.chempartner.com` 被自己的 vhost 认领。

## 坑 4：DNS 未绑定 → 域名 NXDOMAIN

**现象**：`getent/nslookup oligolab.chempartner.com` 返回 NXDOMAIN，外网/内网无法解析到本机。

**根因**：`*.chempartner.com` 子域由公司/公网 DNS 管控，网管还没把 `oligolab` 绑到本机 `10.1.170.84`；本机内部 resolver（k8s 的 10.96.0.3 + 公网 114.114.114.114）都查不到这些子域（连 `admetx.chempartner.com` 也 NXDOMAIN）。

**解决**：需网管/DNS 管理员把 `oligolab.chempartner.com` 解析到 `10.1.170.84`（绑定前域名永远到不了这台服务器，与 nginx/后端无关）。

## 坑 5：5134 数据库的认证盲区（容器化 Postgres）

**现象**：给后端启动时报 `asyncpg ... password authentication failed for user "oligolab"`，`.env` 密码对不上。

**根因链**：
1. 本机 5434 是 **`molcraft-postgres` Docker 容器**（postgres:16-alpine，映射 `0.0.0.0:5434→容器内5432`），承载 bioarch/admetx 等共享库。
2. 该容器**没有 `postgres` 角色**：`-U postgres` → `role "postgres" does not exist`。
3. 容器超管 `molcraft`（`POSTGRES_USER`）被设成 **`NOLOGIN`**：`-U molcraft` → `role "molcraft" is not permitted to log in`（无论 socket 还是 TCP）。
4. 主机侧 `sudo -u postgres psql` 也失败：容器没有主机 socket，peer 认证不成立。

**解决（方案 B，临时 trust 恢复）**：
1. `cp pg_hba.conf pg_hba.conf.bak.<ts>` 备份
2. 在 `pg_hba.conf` 顶部插入 `local all all trust`，`chown 70:70`，`docker kill -s HUP molcraft-postgres` reload
3. 用已有可登录超级用户 **`bioarch`**（`rolsuper=t, rolcanlogin=t`）连接，创建：
   ```sql
   CREATE ROLE oligolab LOGIN PASSWORD '<与.env一致>' CONNECTION LIMIT 20;
   CREATE DATABASE oligolab OWNER oligolab;
   ```
4. **还原**：`cp pg_hba.conf.bak.* pg_hba.conf` + `chown` + reload → 恢复原安全状态

> 关键经验：操作共享生产库前先 `docker inspect` 看清 `POSTGRES_USER` / `POSTGRES_PASSWORD` / 端口映射 / 数据卷（bind `/home/aiuser/data/molcraft-pg`），并确认哪个角色 `rolsuper+t` 且 `rolcanlogin=t`。建库必须用这样的角色，且可登录超用户是 **`bioarch`**（不是 postgres/molcraft）。

## 坑 6：`pg_ctl reload` / 容器命令报 root 或部分命令无效

**现象**：
- `docker exec molcraft-postgres pg_ctl reload` → `pg_ctl: cannot be run as root`。
- 之前 `bash` 里直接敲 SQL（`CREATE ROLE ...`）→ `bash: CREATE: command not found`；以及把 `echo "备份完成"` 误并进 `cp` 命令。

**解决**：
- `pg_ctl` 需以 PG 属主用户跑；容器 reload 直接用 `docker kill -s HUP <容器名>`（发送 HUP 触发 reload，无需进容器终端）。
- SQL 必须通过 `psql -c "..."` 或 `psql <<'SQL' ... SQL` 执行，不能直接敲在 bash。
- 多行命令拆成"一条一条"粘贴，避免花括号/引号/`echo` 粘连出错。

## 坑 7：JWT 时间戳类型（`datetime.utcnow` 弃用 + exp 需为数字）

**现象**：Pyright 告警 `datetime.utcnow` 已弃用；且前端 `isAuthenticated()` 用 `payload.exp * 1000` 判断，若 `exp` 是非数字类型会出错。

**解决**：改用 `datetime.now(timezone.utc)`，并把 `exp`/`iat` 写成 **`int/float` epoch 时间戳**（`expire.timestamp()`）。已验证 `verify_token` 正确返回、前端解析正常。

---

## 运维速查

- 改后端配置：编辑 `.env` → `sudo systemctl restart oligolab`
- 改 nginx：编辑 `/etc/nginx/conf.d/oligolab-chempartner.conf` → `nginx -t && systemctl reload nginx`
- 看日志：`journalctl -u oligolab -f`
- 健康检查：`curl -s http://127.0.0.1:7130/api/health`
- 完整架构见 [`architecture 文档`](./2026-08-26-oligolab-architecture.md)
