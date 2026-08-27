# OligoFormer Off-target —— 踩坑与解决方案记录

记录开发/部署 OligoFormer 内网 SaaS 时遇到的所有问题、根因与修复，供后续维护与复用。

## 环境类

### 1. `download.pytorch.org` 不可达，torch 装不上
- **现象**：`pip install torch ... --index-url .../cu124` 挂起 0 字节；Aliyun 大 wheel 亦超时。
- **根因**：内网对 pytorch 官方 CDN 访问受限；大体积二进制 wheel 传输慢/失败。
- **解决**：不重复下载，**复用本机已有可用 CUDA 环境**（`pepmimic` 的 torch 2.5.1+cu124，H20 已验证），
  把 `torch`、`torchgen` 等 site-packages 文件系统拷贝到 `oligorunner`，再补依赖。
- **经验**：intranet 里优先找本机已有可用 wheel/环境，而不是死磕外部源。

### 2. `conda env create -n X --clone Y` 报错
- **现象**：`UnavailableInvalidChannel: .../anaconda/cloud/nvidia (404)`；`conda create` 读 `.condarc` 里失效的 nvidia 镜像。
- **根因**：`~/.condarc` 配了 Tsinghua 的 `nvidia` 路径（`.../cloud/nvidia` 实际 404）。
- **解决**：`conda create --override-channels -c conda-forge ...` 绕开坏通道；build 大环境时改用文件拷贝，不再依赖 conda 解析。

### 3. 拷贝 torch 后 `import torch` 报一堆缺依赖
- **现象**：依次缺 `typing_extensions`、MKL(`libmkl_intel_lp64.so`)、`libcblas.so.3`、`torchgen`、`joblib`、`mpmath`。
- **根因**：手工拷贝 `torch/` 目录时，它的运行时依赖（MKL/BLAS 共享库、`torchgen` 伴生包、`joblib` 等）没跟着拷全。
- **解决**：从源环境 `pepmimic` 补齐：
  - `lib/` 下的 `libmkl*`、`libcblas*、libblas*、liblapack*`、`libgfortran*`、`libgomp*`
  - `site-packages/` 下的 `torchgen`、`joblib`、`threadpoolctl`、`mpmath`
  - 用 pip 从 Aliyun 补小包（yacs/omegaconf/hydra-core/fsspec/line_profiler 等）。
- **经验**：拷包别只拷主包，共享库与伴生依赖都要。

### 4. numpy 报 “should not try to import numpy from its source directory”
- **现象**：`from numpy.__config__ import show` 抛 ImportError，深层次因是 `libcblas.so.3` 找不到。
- **根因**：numpy 编译期链接的 CBLAS 共享库未随包带全（源 conda 环境有，目标没有）。
- **解决**：把 `libcblas*`/`libblas*`/`liblapack*` 也拷进目标 `lib/`。
- **经验**：这个报错信息很有误导性，一定要看 `Original error was:` 之前的真实 EXC。

### 5. 小包 `pip install` 也超时
- **现象**：`ptflops`、`pytorch-ignite` 安装超时。
- **根因**：`pip install <name>` 会做整棵依赖解析（包括查询 torch 元数据），内网下这步慢。
- **解决**：`pip download --no-deps -d <dir> <pkg>` 直接抓 wheel，再 `pip install --no-deps <wheel>`。
- **经验**：内网装包优先 `--no-deps` + 本地 wheel，避免元数据解析。

## 上游代码 / 集成类

### 6. `scripts/RNA-FM.sh: python: command not found`
- **现象**：核心推理里 `os.system('sh scripts/RNA-FM.sh ...')` 找不到 `python`。
- **根因**：`infer.py` 用 `os.system` 起子 shell，子 shell 拿到的是非 conda 的 PATH；上游假设你已 `source activate`。
- **解决**：SaaS 以子进程调 CLI 时，把 `oligorunner/bin` 放到 `PATH` 最前（runner 已实现），保证子 shell 的裸 `python` 指向正确解释器。
- **位置**：`tools/off-target/service/app/runner.py` 的 `env["PATH"]` 处理。

### 7. `extract_embedding.yml` 的 `PRETRAINED_MODEL_PATH` 指向不存在的 `esm1b...pt`
- **现象**：RNA-FM 想加载 `./pretrained/esm1b_t33_650M_UR50S.pt`，但仓库实际带的是 `RNA-FM_pretrained.pth`。
- **根因**：上游配置文件注释与生效值不一致。
- **解决**：改成 `'./pretrained/RNA-FM_pretrained.pth'`（与 `--model_file` 默认一致）。
- **位置**：`RNA-FM/redevelop/pretrained/extract_embedding.yml`。

### 8. PITA 报 `Permission denied`：ViennaRNA 二进制不可执行
- **现象**：`Progs/RNAfold` 无执行权限。
- **根因**：上游 pita 需先 `make install`（会 `chmod -R 755` 并把 `EXE_BASE_DIR` 硬化成绝对路径）。
- **解决**：在 `off-target/pita` 执行 `make install`，并校验 `RNAfold` 能输出结构。
- **注意**：`make install` 会改写 pita 的 perl 脚本（把相对路径硬编码成绝对路径）；重装/迁移需重跑。
- **位置**：`setup_offtarget.sh` 第 [2/4] 步。

### 9. 脱靶需要 perl 模块，裸 perl 缺 `Statistics::Lite / Bio::TreeIO`
- **解决**：从清华云下 `PerlLib.zip`（含 Bio/TreeIO、Statistics/Lite），`PERL5LIB` 指向 `tools/off-target/PerlLib`；runner 在 `with_off_target` 时注入。
- **位置**：`setup_offtarget.sh`；`runner.py` 的 `PERL5LIB` 注入。

## 应用/挂载类

### 10. 服务端口 8190 被占（comfyui-ui nginx）
- **现象**：启动 uvicorn 报 `address already in use`，访问得到 nginx 502。
- **解决**：改到空闲端口 `7131`（`config.PORT=7131`）。

### 11. SaaS 挂到 `/offtarget/` 子路径后，前端 fetch 用了绝对路径
- **现象**：页面在 `https://.../offtarget/` 下，`fetch('/api/...')` 会打到平台根而不到 off-target 服务。
- **解决**：前端 `api` 帮助函数自动识别 `location.pathname` 中的 `/offtarget/` 前缀生成 `BASE`，对路径做前缀补齐；独立端口（根路径）也兼容。
- **位置**：`service/static/index.html`。

### 12. 平台后端 `/api/modules` 仍旧显示旧状态
- **现象**：改完 `modules_data.py`，但运行中的后端返回“规划中 / url None”。
- **根因**：生产后端未 `--reload`，持旧进程内存。
- **解决**：部署时 `systemctl restart oligolab`（见部署文档步骤 3）。

### 13. systemd 启动 SaaS 报 exit-code=1，但手动跑脚本正常
- **现象**：`systemctl enable --now oligoformer-offtarget` 一直 `activating (auto-restart) / exit-code=1`；手动 `bash run_prod.sh` 却能正常起。
- **根因**：systemd 未设 `WorkingDirectory`，默认 cwd=`/`，而 `uvicorn app.main:app` 需要从 `service/` 目录才能 import `app.main`。脚本此前没 `cd`，依赖“手动在 service/ 目录跑”。
- **解决**：在 `run_prod.sh` 开头 `cd "$(dirname $0)"`（切到脚本所在 `service/` 目录）再 `exec uvicorn`。
- **位置**：`tools/off-target/service/run_prod.sh`。
- **经验**：systemd 环境隔离（cwd=/、PATH/R小）常与手动不一致，凡依赖相对路径/工作目录的脚本必须显式 `cd`。

## 小结

内网部署的关键是「**别硬啃外网大包，善用本机已有环境/二进制**」；遇到误导性报错看真实底层异常；
上游开源项目常假设特定激活/安装前置（source activate / make install），SaaS 封装时要把这些前置显式补齐。
