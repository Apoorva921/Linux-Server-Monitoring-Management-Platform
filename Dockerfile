# ==============================================================================
# SentinelOps - All-in-One Cloud Deployment Dockerfile (Railway / Render / Fly.io)
# Builds React + TypeScript SPA and serves Frontend + FastAPI + WebSockets on $PORT
# ==============================================================================

# Stage 1: Build Frontend SPA
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: Production Python Runtime
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SERVE_STATIC_FRONTEND=true \
    DEMO_MODE=true \
    PORT=8000

WORKDIR /app

RUN groupadd --system sentinelops && useradd --system --gid sentinelops --no-create-home sentinelops

COPY backend/requirements.txt /app/backend/requirements.txt
COPY monitoring-agent/requirements.txt /app/monitoring-agent/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/backend/requirements.txt \
    && pip install -r /app/monitoring-agent/requirements.txt

COPY backend /app/backend
COPY monitoring-agent /app/monitoring-agent
COPY --from=frontend-builder /frontend/dist /app/frontend/dist
COPY scripts/cloud_entrypoint.sh /app/cloud_entrypoint.sh

RUN sed -i 's/\r$//' /app/cloud_entrypoint.sh \
    && chmod +x /app/cloud_entrypoint.sh \
    && chown -R sentinelops:sentinelops /app

USER sentinelops

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"8000\")}/health', timeout=3)" || exit 1

ENTRYPOINT ["/app/cloud_entrypoint.sh"]

