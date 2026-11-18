#!/usr/bin/env sh
set -eu

export SERVE_STATIC_FRONTEND=true
PORT_VAL="${PORT:-8000}"

# Normalize postgres:// URLs (some PaaS providers emit postgres:// instead of postgresql+psycopg://)
if [ -n "${DATABASE_URL:-}" ]; then
  case "$DATABASE_URL" in
    postgres://*)
      export DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}"
      ;;
    postgresql://*)
      export DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}"
      ;;
  esac
fi

echo "[SentinelOps Cloud] Running Alembic migrations..."
cd /app/backend
alembic upgrade head

if [ "${DEMO_MODE:-true}" = "true" ]; then
  echo "[SentinelOps Cloud] Starting Demo Simulator in background (DEMO DATA labeled)..."
  DEMO_API_URL="http://127.0.0.1:${PORT_VAL}" python /app/monitoring-agent/demo_simulator.py &
fi

echo "[SentinelOps Cloud] Starting SentinelOps on 0.0.0.0:${PORT_VAL}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT_VAL}" --proxy-headers --forwarded-allow-ips="*"

