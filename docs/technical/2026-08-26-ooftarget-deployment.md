# OligoFormer Off-target 内网 SaaS —— 部署文档

- 部署目标：让 `https://oligolab.chempartner.com/offtarget/` 可用（nginx 反代到本机 7131）。
- 前置问题总结见：`2026-08-26-ooftarget-pitfalls.md`。

## 0. 已就绪（无需 root）

- [x] `oligorunner` conda 环境（torch 2.5.1 cu124 + H20 可用）。
- [x] 预训练权重：`tools/off-target/OligoFormer/RNA-FM/redevelop/pretrained/RNA-FM_pretrained.pth`（~1.2GB）。
- [x] 独立 SaaS 已在本机 7131 跑通（核心 + 脱靶 + 毒性全链路）。
- [x] 单元测试 4 项通过。
- [x] nginx 站点配置已加 `/offtarget/` location。

## 1. 需要 root 的步骤

> ✅ 已在 `k8s-master02` 执行完毕：systemd 注册 + 启用、nginx `/offtarget/` 生效、`systemctl restart oligolab` 均完成。
> 期间修掉一个 systemd 启动 bug（见 pitfalls #13：run_prod.sh 需 `cd` 到 service 目录）。
> 以下命令仅作备份/复现用。**注意：须在 `/export/projects/sandbox/oligolab` 目录下执行**（相对路径），
> 直接在 `/export/projects` 下跑会 `cannot stat`。

```bash
cd /export/projects/sandbox/oligolab   # ← 先切到项目根
# (1) 部署 off-target 服务为常驻（systemd）
sudo cp infra/systemd/oligoformer-offtarget.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oligoformer-offtarget
# 校验：curl http://127.0.0.1:7131/health

# (2) 部署/刷新 nginx 站点（含 /offtarget/ 反代）
sudo cp /export/projects/sandbox/oligolab/infra/nginx/oligolab-chempartner.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl reload nginx

# (3) 重启主平台后端，使 off-target 模块状态/URL 生效
sudo systemctl restart oligolab        # (如已按 infra/systemd/oligolab.service 注册)
```

## 2. 数据库（主平台，如需）

OligoFormer 推理本身**不需要数据库**。主平台的用户/登录需 Postgres `oligolab` 库：
```bash
# pg 超管执行 infra/db/create_oligolab_db.sql（改强密码回填 .env）
# 或 bash infra/db/reset_and_create_oligolab.sh（重置开发库）
```

## 3. 验证清单

1. `curl http://127.0.0.1:7131/health` → `{"status":"ok"}`
2. 浏览器访问 `https://oligolab.chempartner.com/offtarget/` → 出现 OligoFormer 页面
3. 平台首页 → 脱靶与靶点预测卡片 → 「打开工具」→ 新标签页进入 `/offtarget/`
4. 提交一条 ≥19nt 的 mRNA → 轮询出排序结果（核心 26s，脱靶 ~8min）

## 4. 常驻维护

- 服务日志：`journalctl -u oligoformer-offtarget -f`
- 推理临时目录（可清理）：`tools/off-target/OligoFormer/data/infer/job_*`、`result/*.txt`
- 异常时由 `Restart=always` 自动拉起。
