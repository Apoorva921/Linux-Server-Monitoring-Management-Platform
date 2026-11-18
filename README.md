# SentinelOps — Linux Server Monitoring & Management Platform

**SentinelOps** is a production-style, centralized Linux server monitoring, alerting, and log observability platform engineered with **FastAPI**, **PostgreSQL**, **SQLAlchemy + Alembic**, **WebSockets**, **React + TypeScript + Tailwind CSS + Recharts**, **psutil**, **Nginx**, and **Docker Compose**.

---

## 1. Project Overview

SentinelOps enables systems engineers and infrastructure teams to monitor multiple Linux servers from a unified dark-mode observability dashboard. Lightweight Python monitoring agents run on each host under least-privilege Linux permissions, collect real OS metrics and system logs, and stream them via authenticated HTTP requests to a central FastAPI backend backed by PostgreSQL and live WebSocket broadcasting.

## 2. Problem Statement

Production Linux fleets frequently suffer from fragmented visibility: resource spikes go unnoticed until outages occur, raw `/var/log` files are scattered across machines, cumulative network counters are easily misread as live bandwidth, and naive alerting scripts create notification storms on every polling cycle.

## 3. Objectives

- Collect **real** Linux host metrics (CPU, RAM, swap, disk partitions, network counters & delta throughput, load averages, uptime, running processes) and approved system logs (`/var/log/syslog`, `/var/log/auth.log`, `journalctl`).
- Provide secure agent registration with per-server HMAC-hashed API tokens and JWT-authenticated user access (`admin` / `viewer` RBAC).
- Evaluate configurable warning/critical alert thresholds with **duplicate suppression**, **severity escalation**, **cooldown windows**, and **automatic recovery detection**.
- Compute a transparent, deterministic **0–100 Health Score** with explicit factor-by-factor deductions.
- Deliver real-time updates to the web dashboard over authenticated **WebSockets** without page refreshes.
- Support both **Mode A (Real Linux Servers)** and **Mode B (Demo Simulator)** with explicit `DEMO DATA` labeling.

## 4. Key Features

| Module | Capabilities |
| :--- | :--- |
| **Authentication & RBAC** | Bcrypt password hashing, JWT Bearer auth, `admin` & `viewer` roles, rate-limited auth endpoints, protected routes. |
| **Infrastructure Overview** | Live fleet KPIs (online/offline/warning/critical hosts, active alerts, avg CPU/RAM/Disk, network rate), live charts, server health table, recent alerts & logs. |
| **Server Management** | Register new monitoring agents, one-time API token issuance & rotation, host inventory, individual server detail pages. |
| **Real-Time Telemetry** | Authenticated `WS /ws/metrics` with auto-reconnect, deduplicated topic subscriptions, connection status pill, and historical range selectors (`15m`, `1h`, `6h`, `24h`, `7d`). |
| **Alert Management** | Default & configurable CPU/RAM/Disk/Network thresholds, deduplication, escalation (`warning` → `critical`), cooldown, recovery detection, acknowledge & resolve actions. |
| **System Log Explorer** | Restricted read-only collection of `/var/log/syslog`, `/var/log/auth.log`, and `journalctl`; keyword search; severity, server, and date filters; highlighted errors/warnings. |
| **Process Monitor** | Read-only running process inspection (`PID`, name, user, status, CPU %, memory %) with search & sorting; process termination intentionally disabled. |
| **Deterministic Health Score** | Transparent 0–100 score calculated from CPU, memory, disk, availability, and active alert penalties with clear textual explanations. |
| **Network Monitoring** | Separates live upload/download throughput (`B/s`, computed via counter deltas) from cumulative counters (bytes/packets sent & received since boot). |
| **Settings & Retention** | Configurable collection interval, offline heartbeat timeout, metric/log retention pruning, log sources, and global alert thresholds. |

## 5. Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 16 (`psycopg`), bcrypt, PyJWT, WebSockets.
- **Monitoring Agent**: Python, `psutil`, `/proc` & `/etc/os-release` readers, `requests`, systemd unit hardening.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Axios, React Router.
- **Infrastructure**: Docker, Docker Compose, Nginx reverse proxy (REST + WebSocket + SPA).
- **Testing**: Pytest, FastAPI `TestClient`, Vitest, React Testing Library.

## 6. System Architecture

See detailed architecture notes and sequence diagrams in:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md)

```mermaid
flowchart LR
    Agents["Linux Monitoring Agents\n(Ubuntu / Debian / Demo Simulator)"] -->|POST /api/metrics/ingest\nX-Agent-Token| Nginx["Nginx Reverse Proxy (:8080)"]
    Browser["React + TypeScript Dashboard"] -->|REST (JWT) + WS /ws/metrics| Nginx
    Nginx --> Backend["FastAPI Backend (:8000)\nAuth · Ingestion · Alert Engine · Health Scoring · WS Manager"]
    Backend --> Postgres[("PostgreSQL 16\n8 Normalized Tables")]
```

## 7. Database Schema

SentinelOps uses 8 PostgreSQL tables managed via SQLAlchemy ORM and Alembic migrations (`backend/alembic/versions/0001_initial_schema.py`):

1. `users` — User accounts, bcrypt password hashes, and roles (`admin` | `viewer`).
2. `servers` — Registered host metadata, heartbeat timestamp, status, and deterministic health score explanation.
3. `agent_tokens` — HMAC-SHA256 hashed per-server API tokens with display prefixes and revocation timestamps.
4. `server_metrics` — Time-series CPU, memory, disk, network (counters + throughput), load average, and process snapshots (UTC timestamps, composite `(server_id, timestamp)` index).
5. `alert_rules` — Global and per-server warning/critical thresholds and cooldown periods.
6. `alerts` — Active, acknowledged, and resolved threshold alerts.
7. `system_logs` — Parsed syslog/auth.log/journald entries indexed by `(server_id, timestamp)` and `(severity, timestamp)`.
8. `system_settings` — Global monitoring interval, offline timeout, retention days, and log collection settings.

Full ER diagram: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

## 8. API Documentation

When running, interactive OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8080/docs` (or `http://localhost:8000/docs`)
- ReDoc: `http://localhost:8080/redoc`

Complete endpoint reference: [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

## 9. Installation & Local Development Instructions

### Prerequisites
- Docker & Docker Compose (recommended for full-stack execution)
- Or for local development: Python 3.11+, Node.js 20+, PostgreSQL 16

### Environment Configuration
```bash
cp .env.example .env
# Edit .env and set a strong SECRET_KEY and INITIAL_ADMIN_PASSWORD
```

## 10. Docker Deployment (Recommended)

### Mode A — Production / Real Linux Servers (No Simulated Data)
```bash
docker compose up --build
```
Access the platform at:
- **Dashboard**: `http://localhost:8080`
- **Swagger API Docs**: `http://localhost:8080/docs`
- **Health Check**: `http://localhost:8080/health`

Default bootstrap administrator credentials (configurable in `.env`):
- **Username**: `admin`
- **Password**: `Admin@SentinelOps123!`

### Mode B — Demo Mode (4 Simulated Linux Servers, Clearly Labeled `DEMO DATA`)
```bash
docker compose --profile demo up --build
```
The Demo Simulator registers 4 simulated hosts (`prod-web-01 [DEMO]`, `prod-db-01 [DEMO]`, `worker-batch-02 [DEMO]`, `edge-cache-03 [DEMO]`) through the real API and streams realistic metrics, threshold spikes, recoveries, and logs—every single record is tagged `is_demo: true` and badged **`DEMO DATA`** in the UI.

## 11. Ubuntu Linux Monitoring Agent Setup (Mode A)

1. Sign in to the SentinelOps dashboard as an Administrator, open **Servers → Register Agent**, and copy the generated `SERVER_ID` and one-time `API_TOKEN` (`sops_...`).
2. On your target Ubuntu 22.04 / 24.04 server, run the least-privilege installer script:
   ```bash
   sudo bash scripts/install_agent_ubuntu.sh \
     --api-url http://<SENTINELOPS_HOST>:8080 \
     --server-id <SERVER_UUID> \
     --api-token <sops_API_TOKEN>
   ```
3. Verify the systemd service (runs as non-root `sentinelops` user with read-only `adm` and `systemd-journal` group memberships):
   ```bash
   sudo systemctl status sentinelops-agent
   journalctl -u sentinelops-agent -f
   ```

To test a single real collection cycle without installing systemd:
```bash
cd monitoring-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SENTINELOPS_API_URL=http://localhost:8000 \
SENTINELOPS_SERVER_ID=<SERVER_UUID> \
SENTINELOPS_API_TOKEN=<sops_API_TOKEN> \
python agent.py --once
```

## 12. Environment Configuration

All configuration keys are documented in [.env.example](.env.example). Never commit `.env` or agent tokens to version control.

## 13. Running Automated Tests

### Backend Tests (Pytest + FastAPI TestClient)
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pytest tests -v
```

### Monitoring Agent Collector & Log Parser Tests
```bash
pytest monitoring-agent/tests -v
```

### Frontend Tests & Production Build (Vitest + React Testing Library)
```bash
cd frontend
npm install
npm test
npm run build
```

## 14. Screenshots & Dashboard Views

After starting SentinelOps with `docker compose --profile demo up --build`, explore each view at `http://localhost:8080`:
- **Overview (`/`)**: Fleet KPI cards, live CPU/Memory/Network Recharts visualizations, Server Health table, recent alerts & system events, and `DEMO DATA` banner.
- **Servers (`/servers`) & Server Detail (`/servers/:id`)**: Host inventory, Register Agent credential modal, deterministic Health Score deduction breakdown, live per-host charts, cumulative vs throughput network cards, top processes, and server logs.
- **Monitoring (`/monitoring`)**: Dedicated real-time WebSocket telemetry stream with time-range toggles.
- **Alerts (`/alerts`)**: Alert summary counters, severity/status/server filters, Acknowledge and Resolve workflow.
- **Logs (`/logs`)**: Full-text log search, severity/server/date filters, error/warning row highlighting.
- **Processes (`/processes`)**: Read-only process explorer with live search and multi-column sorting.
- **Settings (`/settings`)**: Configurable monitoring interval, retention policy, alert thresholds, and log collection sources.

## 15. Limitations

- **Process Control**: Process termination/restarting is intentionally disabled in v1 to preserve least-privilege security.
- **Rate Limiting Store**: The built-in auth rate limiter is in-memory per backend worker; multi-replica deployments should back it with Redis.
- **Time-Series Storage**: Standard PostgreSQL tables with composite indexes and automated retention pruning are used; very large fleets (>500 hosts) would benefit from TimescaleDB hypertables.
- **Alert Delivery**: Alerts are persisted in PostgreSQL and pushed over WebSockets; external webhooks (Slack/PagerDuty/Email) are not yet wired.

## 16. Future Improvements

- TimescaleDB hypertables & continuous aggregates for long-term metric compression.
- Webhook, Email (SMTP), and Slack/PagerDuty alert notification channels.
- Mutual TLS (mTLS) between monitoring agents and the ingestion gateway.
- Redis-backed Pub/Sub for horizontal scaling of WebSocket workers and distributed rate limiting.
- Per-server custom alert rule editor in the UI.

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

