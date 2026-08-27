# OligoFormer 脱靶与靶点预测模块 —— 设计与接入文档

- 日期：2026-08-26
- 状态：**已上线（内网验证版）**
- 所属平台模块：`off-target`（脱靶与靶点预测）
- 代码位置：`tools/off-target/`

## 1. 背景与定位

OligoLab 平台第 7 个模块「脱靶与靶点预测」原为占位。经比对其规划能力与开源项目 OligoFormer
（清华 lulab，`https://github.com/lulab/OligoFormer`，transformer 架构 + RNA-FM 预训练）后，
判定 **OligoFormer 与本模块高度匹配**：
- 核心：siRNA 功效预测（对应「靶点筛选 / 特异性评估」）
- 可选：脱靶预测（PITA / TargetScan，对应「脱靶打分」）
- 可选：毒性筛选（对应「稳定性/毒副作用」初筛）

因此把 OligoFormer 作为该模块的计算内核，封装为独立内网 SaaS，供内部用户验证，验证 OK
后再挂载到平台 `off-target` 模块下。

## 2. 总体架构

```
用户浏览器
   │  （平台内）https://oligolab.chempartner.com/offtarget/    ← 通过 nginx 挂载
   │  （独立验证）http://127.0.0.1:7131
   ▼
OligoFormer 内网 SaaS (FastAPI, tools/off-target/service, 127.0.0.1:7131)
   ├── /              托管 web UI（单词页，提交 mRNA → 展示排序结果）
   ├── /api/predict   提交推理任务
   ├── /api/jobs      任务列表 / 单个任务（轮询结果）
   └── /health        健康检查
   │     串行任务队列（GPU 重型推理，默认 1 并发）
   ▼
OligoFormer CLI (tools/off-target/OligoFormer)
   ├── scripts/main.py --infer 1 -i1 <mRNA.fa> [-off] [-tox]
   ├── RNA-FM 特征提取（RNA-FM_pretrained.pth, ~1.2GB）
   ├── best_model.pth（siRNA 功效 transformer 模型）
   └── off-target（pita / targetscan，perl + ViennaRNA-1.6 预编译二进制）
```

- **推理环境**：`oligorunner` conda 环境（Python 3.10，torch 2.5.1 + cu124，跑在 H20 GPU）。
- **服务环境**：复用 oligolab 后端轻量 `.venv`（Python 3.11 + FastAPI/uvicorn），只负责调度与解析，
  重型推理通过子进程交给 `oligorunner`，职责分离、崩溃隔离。

## 3. 目录结构

```
tools/off-target/
├── OligoFormer/                    # git clone 的上游源码（含模型权重、RNA-FM、off-target 脚本）
├── PerlLib/                        # 清华云下载的 perl 模块（Bio/TreeIO、Statistics/Lite）
├── service/
│   ├── app/
│   │   ├── config.py                # 路径 / 端口 / 推理环境 python 配置
│   │   ├── runner.py                # 推理封装：子进程跑 CLI + 解析结果 + 任务管理器
│   │   └── main.py                  # FastAPI 入口
│   ├── static/index.html            # 单页 web UI
│   ├── test_runner.py               # 单元测试（核心 4 项 + 重型集成 1 项，默认跳过）
│   ├── run_prod.sh / run_dev.sh     # 启停脚本
│   └── oligoformer-offtarget.service
├── setup_offtarget.sh               # 一次性初始化（perl/pita/参考序列/RNAfold 校验）
```

## 3.1 模型与数据下载（不纳入 git，需自行获取）

> **重要**：`OligoFormer/` 上游源码连同 **RNA-FM 预训练权重（~1.2GB）** 等大文件**不入库**（见 `.gitignore`）。
> 部署机器按 `setup_offtarget.sh` + 下面链接获取。所有链接均来自上游 README / 清华云。

| 资源 | 大小 | 下载链接 | 落盘位置 |
|---|---|---|---|
| RNA-FM 打包包（含 `RNA-FM_pretrained.pth`） | ~1.2GB | `https://cloud.tsinghua.edu.cn/f/46d71884ee8848b3a958/?dl=1`（存为 `RNA-FM.tar.gz` 后解压） | `OligoFormer/RNA-FM/redevelop/pretrained/RNA-FM_pretrained.pth` |
| PerlLib（perl 模块：Bio/TreeIO、Statistics/Lite） | ~2.4MB | `https://cloud.tsinghua.edu.cn/f/cab2afdf951140a48fec/?dl=1`（存为 `PerlLib.zip` 后解压到 `tools/off-target/PerlLib`） | `tools/off-target/PerlLib/` |
| OligoFormer `best_model.pth` / `mismatch_model.pth` | 5.8MB / 78KB | **git 自带**（`OligoFormer/model/`，随上游仓库 clone 即得，无需下载） | `OligoFormer/model/` |
| 人类 UTR/ORF 参考序列（用于脱靶全人类扫描） | 42/48MB（zip） | **git 自带**（`OligoFormer/off-target/ref/*.zip`，`setup` 时解压） | `OligoFormer/off-target/ref/` |

- RNA-FM 也可从上游备用源（GitHub `ml4bio/RNA-FM` + Google Drive `1VGye74GnNXbUMKx6QYYectZrY7G2pQ_J`）获取，内网优先用清华云。
- 上述链接与命令在 `setup_offtarget.sh` 中已引用；PITA/ViennaRNA-1.6 二进制随上游仓库提供。

## 4. 模块能力与接口

### 4.1 推理能力矩阵
| 能力 | 上游开关 | 产出列 |
|---|---|---|
| 功效预测 | 默认 | `sense, siRNA, efficacy` |
| 功能过滤 | 默认（可 -nf 关） | `func_filter` |
| 脱靶预测 | `-off` | `pita_score, targetscan_score, off_target_filter` |
| 毒性筛选 | `-tox` | `cell_viability, toxicity_filter` |
| 汇总过滤 | 组合 | `filter`（越小越优，0 最佳） |

### 4.2 HTTP API
- `POST /api/predict`：`{sequence, name, with_off_target, with_toxicity, no_func, top_n}` → `{job_id}`
- `GET /api/jobs`：任务列表
- `GET /api/jobs/{id}`：单个任务（`status`: queued/running/done/error；`result`: 排序后的 siRNA 行）

### 4.3 性能
- 核心功效预测：38 窗口 / 26s（H20）。
- 加脱靶（100-seq 参考集）：~8 min。全人类参考集（`-a`）更慢，用于正式筛选。

## 5. 挂载到平台

1. 前端 `Module.tsx`：当模块含 `url` 时显示「打开工具（新标签页）」。
2. `modules.ts` / `modules_data.py`：off-target 状态更新为「建设中·验证中」，`url=/offtarget/`。
3. nginx：在 oligolab 站点加 `/offtarget/` location → `127.0.0.1:7131`（`proxy_pass .../;` 去掉前缀）。
   web UI 的 JS 通过 `BASE` 自动识别 `/offtarget/` 前缀，独立端口与挂载子路径均可用。

## 6. 复用与合规

- OligoFormer 授权为**学术/非商业**，**商业使用需清华授权**（见其 LICENSE）。内网 SaaS 若涉商业用途需先确认。
- RNA-FM 预训练权重（~1.2GB）与 PerlLib 来自清华云；PITA/ViennaRNA-1.6 随上游仓库提供。
- 所有重型计算在 H20 GPU / oligorunner 环境完成，服务进程保持轻量。
