#!/usr/bin/env bash
# 初始化 OligoFormer off-target 依赖（perl 模块 / PITA 安装 / 人 UTR-ORF 参考 / PERL5LIB）
# 在仓库根 offline 环境执行一次即可。用法: bash setup_offtarget.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # off-target 目录
OF="$ROOT/OligoFormer"
PERLLIB="$ROOT/PerlLib"

echo ">>> [1/4] 下载并解压 PerlLib（BIO / Statistics 模块），目标: $PERLLIB"
if [ ! -f "$PERLLIB/Statistics/Lite.pm" ]; then
  curl -sL "https://cloud.tsinghua.edu.cn/f/cab2afdf951140a48fec/?dl=1" -o /tmp/PerlLib.zip
  (cd "$ROOT" && rm -rf PerlLib && unzip -q /tmp/PerlLib.zip -d .)
fi
echo "      PERL5LIB 请设为: $PERLLIB"

echo ">>> [2/4] PITA make install（把 EXE_BASE_DIR 硬化成绝对路径 + chmod 可执行）"
(cd "$OF/off-target/pita" && make install >/dev/null)

echo ">>> [3/4] 解压 human UTR/ORF 参考序列"
(cd "$OF/off-target/ref" && unzip -o human_UTR.txt.zip >/dev/null && unzip -o human_ORF.txt.zip >/dev/null)

echo ">>> [4/4] 校验 RNAfold 可用"
if printf 'ACGUACGU\n' | "$OF/off-target/pita/Bin/ViennaRNA/ViennaRNA-1.6/Progs/RNAfold" >/dev/null; then
  echo "      RNAfold OK"
else
  echo "      RNAfold 失败，请检查二进制权限" && exit 1
fi

echo ">>> 完成。"
