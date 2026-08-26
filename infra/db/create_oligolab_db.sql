-- OligoLab 独立数据库/角色（需以 Postgres 超级用户在 127.0.0.1:5434 上执行一次）
-- 请先把下面的密码改为强密码，再执行。
-- 执行示例（root or DBA）：
--   psql -h 127.0.0.1 -p 5434 -U postgres -f infra/db/create_oligolab_db.sql
-- 之后把该密码填入 /export/projects/sandbox/oligolab/.env 的 OLIGOLAB_PG_PASSWORD

CREATE ROLE oligolab LOGIN PASSWORD 'change-me' CONNECTION LIMIT 20;
CREATE DATABASE oligolab OWNER oligolab;
