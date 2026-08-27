# off-target 模块（OligoFormer 脱靶与靶点预测）

OligoLab 平台 `off-target` 模块的计算内核与独立内网 SaaS。

## 组成
| 目录/文件 | 说明 |
|---|---|
| `OligoFormer/` | 上游源码（git clone 清华 lulab），含模型权重、RNA-FM、off-target 脚本 |
| `PerlLib/` | 清华云下载的 perl 模块（脱靶 pita/targetscan 需要） |
| `service/` | 独立内网 SaaS（FastAPI + 单页 UI，端口 7131） |
| `setup_offtarget.sh` | 一次性初始化（perl/pita/参考序列/RNAfold 校验） |

## 快速验证
1. `bash setup_offtarget.sh`（首次）
2. `cd service && bash run_dev.sh` → 打开 `http://127.0.0.1:7131/`
3. 粘贴 ≥19nt mRNA，勾选脱靶/毒性 → 预测

## 模型下载（大文件不入库，按此拉取）
| 资源 | 链接 | 落盘 |
|---|---|---|
| RNA-FM 权重（~1.2GB） | `https://cloud.tsinghua.edu.cn/f/46d71884ee8848b3a958/?dl=1` → `RNA-FM.tar.gz` + 解压 | `OligoFormer/RNA-FM/redevelop/pretrained/RNA-FM_pretrained.pth` |
| PerlLib（perl 模块） | `https://cloud.tsinghua.edu.cn/f/cab2afdf951140a48fec/?dl=1` → `PerlLib.zip` + 解压 | `PerlLib/` |

（`best_model.pth`、UTR/ORF 参考随上游 git 自带，无需下载。）详细见
`docs/technical/2026-08-26-ooftarget-design.md` 第 3.1 节。

## 关键文档
- 设计：`docs/technical/2026-08-26-ooftarget-design.md`
- 部署（root）：`docs/technical/2026-08-26-ooftarget-deployment.md`
- 踩坑：`docs/technical/2026-08-26-ooftarget-pitfalls.md`
- 交付说明：`docs/technical/2026-08-26-ooftarget-delivery.md`

## 前提
- GPU（H20，CUDA 12.4）
- `oligorunner` conda 环境（Python3.10 + torch 2.5.1 cu124）
- 平台轻量 `.venv`（Python3.11 + FastAPI）用于跑 SaaS 调度

> ⚠️ OligoFormer 学术/非商业免费，商业使用需清华授权。
