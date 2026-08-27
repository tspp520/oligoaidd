#!/bin/bash
# 以 root 运行：借助 postgres OS 用户的本地 peer 认证，无需记住超管密码即可：
#  1) 创建 oligolab 角色/库（从 create_oligolab_db.sql 读取）
#  2) （可选）重置 postgres 超管密码
# 用法：sudo bash infra/db/reset_and_create_oligolab.sh
set -e
cd "$(dirname "$0")"

NEW_SUPER_PW="Postgres_Oligo_Change_Me_$(date +%s)"  # 仅当你要重置超管密码时用

echo "=== 1) 用 postgres OS 用户(peer) 创建 oligolab 角色/库 ==="
# 从 SQL 读到的密码就是我们在 .env 里填好的那个（已经在 create_oligolab_db.sql 里写好了）
if id postgres >/dev/null 2>&1; then
  sudo -u postgres psql -d postgres -f create_oligolab_db.sql
  echo "oligolab 库/角色创建完成"
else
  echo "本机无 postgres 系统用户，请改用：psql -h 127.0.0.1 -p 5434 -U <超管> -f create_oligolab_db.sql"
  exit 1
fi

echo
echo "=== 2)（可选）重置 postgres 超管密码（若你后续想用 -U postgres -h 127.0.0.1 登录） ==="
read -r -p "是否重置 postgres 超管密码？[y/N] " ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
  sudo -u postgres psql -d postgres -c "ALTER USER postgres WITH PASSWORD '$NEW_SUPER_PW';"
  echo "超管密码已重置为: $NEW_SUPER_PW  （请记下）"
else
  echo "跳过重置超管密码。"
fi

echo
echo "=== 完成。现在可启动后端 ==="
echo "  systemctl enable --now oligolab   # 或  cd /export/projects/sandbox/oligolab && ./backend/run_prod.sh"
