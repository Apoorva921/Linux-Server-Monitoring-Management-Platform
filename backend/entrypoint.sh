#!/usr/bin/env sh
set -eu

echo "[SentinelOps Backend] Running Alembic database migrations..."
alembic upgrade head

echo "[SentinelOps Backend] Starting Uvicorn API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"

