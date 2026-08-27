# OligoFormer 内网 SaaS（脱靶与靶点预测）

基于清华 lulab 的 OligoFormer，提供 siRNA 功效预测、脱靶（PITA/TargetScan）与毒性筛选的
内网 Web 服务，挂载到 OligoLab 平台 `off-target` 模块。

## 快速开始

```bash
# 1) 初始化依赖（perl / pita / 参考序列 / RNAfold 校验），只需一次
bash ../setup_offtarget.sh

# 2) 启动服务（复用平台 .venv，重型推理交给 oligorunner conda 环境）
bash run_dev.sh          # 开发，热重载
# 或 bash run_prod.sh    # 生产
```

访问 `http://127.0.0.1:7131/`。

## 目录
- `app/`：FastAPI（config / runner / main）
- `static/index.html`：单页 UI
- `test_runner.py`：单元测试

## 单元测试
```bash
# 快速（核心 4 项，~55s，GPU 需要）
/home/aiuser/.conda/envs/oligorunner/bin/python -m pytest test_runner.py -v

# 含重型脱靶集成（~8min）
RUNSLOW=1 /home/aiuser/.conda/envs/oligorunner/bin/python -m pytest test_runner.py -v
```

## API
- `POST /api/predict` → `{job_id}`  （body: sequence/name/with_off_target/with_toxicity/no_func/top_n）
- `GET /api/jobs` / `GET /api/jobs/{id}` → 结果（result: 按 efficacy 排序的 siRNA 行）

## UI：示例序列自动补全
mRNA 输入框下方有「从示例自动补全」输入框（`list="mrnaExamples"` datalist）。
输入与四个内置示例序列任意匹配（忽略大小写/T）时即时回填到上方 mRNA 输入框；点选/Tab/回车选中也会填入。
这样"占位提示语"(placeholder)可一键实体化为真实序列。

详见 `docs/technical/2026-08-26-ooftarget-design.md`。
