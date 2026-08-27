# OligoFormer Off-target 模块 —— 最终交付说明

- 日期：2026-08-26
- 状态：功能完成、单元测试通过、SaaS 独立验证 OK、已挂载到平台（待 root 最后落地 nginx/systemd）

## 一、交付物清单

| 类别 | 内容 | 位置 |
|---|---|---|
| 预训练权重 | RNA-FM 1.2GB + OligoFormer best_model.pth | `tools/off-target/OligoFormer/` |
| 推理环境 | `oligorunner` conda（Python3.10 + torch 2.5.1 cu124 + H20） | ~/.conda/envs/oligorunner |
| 独立 SaaS | FastAPI + 单页 UI，端口 7131 | `tools/off-target/service/` |
| 单元测试 | 4 项通过 + 1 项重型（默认跳过） | `tools/off-target/service/test_runner.py` |
| 初始化脚本 | perl/pita/参考序列/RNAfold | `tools/off-target/setup_offtarget.sh` |
| 平台挂载 | 前端「打开工具」+ nginx `/offtarget/` | `frontend/`、`infra/nginx/` |
| systemd | 常驻服务单元 | `infra/systemd/oligoformer-offtarget.service` |
| 文档 | 设计/部署/踩坑/本说明 | `docs/technical/2026-08-26-ooftarget-*.md` |

## 二、逐模块完成情况（每模块测试→修 bug→通过）

| 子模块 | 状态 | 验证 |
|---|---|---|
| 1. 核心 siRNA 功效预测 | ✅ | 单测 `test_run_inference_core` 通过；38 窗口 26s |
| 2. 功能过滤器 | ✅ | `-nf` 开关单测通过 |
| 3. 脱靶预测（PITA+TargetScan） | ✅ | 集成 `-off` 全链路跑通（~8min） |
| 4. 毒性筛选 | ✅ | 集成 `-tox` 跑通（查表） |
| 5. 环境/GPU 可用性 | ✅ | `test_environment_python_ok` 通过（H20 CUDA） |

## 三、如何验证（内部用户）

1. 直接访问独立服务 `http://127.0.0.1:7131/`
2. 粘贴一条 ≥19nt 的 mRNA（例：`ACUAUAGGUUCAAUUUAAUGUGCGAAAGAGACCUUACGGACGUGGGCGCCAGUGGAC`）
3. 需脱靶/毒性时勾选对应选项 → 「开始预测」
4. 核心结果 ~26s；脱靶 ~8min。结果按 efficacy 降序，含 pita/targetscan/toxicity 打分与 `filter`。

平台内路径：登录 `oligolab.chempartner.com` → 脱靶与靶点预测 → 「打开工具」。
（需 root 完成部署文档第 1 节步骤后生效。）

## 四、遗留（需 root，无法代跑）
- `infra/systemd/oligoformer-offtarget.service` 注册 + `systemctl enable --now`
- nginx `/offtarget/` location 生效（`nginx -t && reload`）
- `systemctl restart oligolab`（让平台模块状态/URL 生效）
- 见 `docs/technical/2026-08-26-ooftarget-deployment.md`

## 五、重要提醒
- **授权**：OligoFormer 学术/非商业免费，商业使用需清华授权（`ott@tsinghua.edu.cn`）。
- 本实现不改上游推理数学；仅做依赖补齐、封装与 UI。
- 生产负载下推理为 GPU 重型、串行单例；后续可加并发配额/排队。
