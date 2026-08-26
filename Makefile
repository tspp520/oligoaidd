.PHONY: db-create dev build prod

# 在 5434 上创建独立库/用户（需 pg 超管执行）
db-create:
	@echo "请以 pg superuser 在 127.0.0.1:5434 执行 infra/db/create_oligolab_db.sql"
	@echo "  psql -h 127.0.0.1 -p 5434 -U postgres -f infra/db/create_oligolab_db.sql"

# 后端开发模式
dev:
	./backend/run_dev.sh

# 构建前端
build:
	cd frontend && npm run build

# 生产启动（gunicorn 多 worker）
prod:
	./backend/run_prod.sh
