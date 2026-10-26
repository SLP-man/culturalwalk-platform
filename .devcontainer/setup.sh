#!/usr/bin/env bash
# Dev Container 首次创建后执行：装依赖、起依赖服务、跑迁移。
# 目标：新人 clone 后 30 分钟内能跑起来（docs/04 §1）。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 后端依赖"
cd services/api
python -m venv .venv
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e ".[dev]"
cp -n ../../infra/.env.example .env || true
cd ../..

echo "==> 前端依赖"
cd apps/web
corepack enable
pnpm install
cd ../..

echo "==> 起依赖服务"
docker compose -f infra/docker-compose.yml up -d db minio
echo "等待数据库就绪…"
for _ in $(seq 1 30); do
  if docker compose -f infra/docker-compose.yml exec -T db pg_isready -U cw >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "==> 迁移"
cd services/api
. .venv/bin/activate
alembic upgrade head || echo "（还没有迁移文件，先跳过）"
cd ../..

echo
echo "完成。两种启动方式："
echo "  cd services/api && . .venv/bin/activate && uvicorn app.main:app --reload"
echo "  cd apps/web && pnpm dev"
