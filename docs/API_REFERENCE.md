# SentinelOps REST & WebSocket API Reference

Interactive OpenAPI / Swagger UI documentation is automatically served at `/docs` and ReDoc at `/redoc` when the backend is running.

## Authentication Headers

- **User endpoints**: `Authorization: Bearer <jwt_access_token>`
- **Monitoring agent endpoints**: `X-Agent-Token: <agent_api_token>`
- **WebSocket endpoint**: `ws://<host>/ws/metrics?token=<jwt_access_token>`

## 1. Authentication (`/api/auth`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Public (rate-limited) | Register a new user (`viewer` by default; first user or admin can create `admin`). |
| `POST` | `/api/auth/login` | Public (rate-limited) | Authenticate with username/email and password; returns JWT access token. |
| `GET` | `/api/auth/me` | User JWT | Return currently authenticated user profile and role. |

## 2. Servers (`/api/servers`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/servers` | User JWT | Paginated list of registered servers with latest status, health score, and filters (`status`, `search`, `is_demo`). |
| `POST` | `/api/servers/register` | Admin JWT | Register a new server and issue a one-time agent API token (`sops_...`). |
| `GET` | `/api/servers/{server_id}` | User JWT | Retrieve full server metadata, latest metrics snapshot, and health score breakdown. |
| `POST` | `/api/servers/{server_id}/rotate-token` | Admin JWT | Revoke old agent tokens and issue a fresh agent API token. |
| `DELETE` | `/api/servers/{server_id}` | Admin JWT | Delete a server and cascade-remove its tokens, metrics, alerts, and logs. |

## 3. Monitoring & Ingestion (`/api/metrics`, `/api/servers/{id}/*`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/metrics/ingest` | Agent Token | Ingest CPU, memory, disk, network (counters + throughput), load, uptime, and process snapshot. Triggers health scoring, alert evaluation, and WebSocket broadcast. |
| `GET` | `/api/servers/{server_id}/metrics` | User JWT | Get the latest metric snapshot and health explanation for a server. |
| `GET` | `/api/servers/{server_id}/metrics/history` | User JWT | Get historical time-series metrics (`range=15m|1h|6h|24h|7d`, `limit=1..1000`). |
| `GET` | `/api/servers/{server_id}/processes` | User JWT | Get latest running processes with `search`, `sort_by` (`cpu_percent|memory_percent|pid|name`), and `order` (`asc|desc`). |

## 4. Alerts (`/api/alerts`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/alerts` | User JWT | Paginated alerts with filters (`severity`, `status`, `server_id`, `metric_type`). |
| `GET` | `/api/alerts/{alert_id}` | User JWT | Retrieve single alert detail. |
| `PATCH` | `/api/alerts/{alert_id}/acknowledge` | User JWT | Mark an active alert as acknowledged by the current user. |
| `PATCH` | `/api/alerts/{alert_id}/resolve` | User JWT | Manually mark an alert as resolved. |

## 5. System Logs (`/api/logs`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/logs/ingest` | Agent Token | Batch ingest parsed log entries from a monitoring agent. |
| `GET` | `/api/logs` | User JWT | Paginated logs with filters (`server_id`, `severity`, `source`, `start_date`, `end_date`). |
| `GET` | `/api/logs/search` | User JWT | Keyword search (`q`) combined with `server_id`, `severity`, `source`, `start_date`, `end_date`. |

## 6. Settings (`/api/settings`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/settings` | User JWT | Fetch monitoring interval, retention policy, log sources, and global alert thresholds. |
| `PUT` | `/api/settings` | Admin JWT | Update global monitoring settings and alert rule thresholds. |

## 7. Health & Dashboard Summary

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Health check verifying API status and PostgreSQL connectivity. |
| `GET` | `/api/dashboard/summary` | User JWT | Fleet overview: server counts, active/critical alert counts, fleet average CPU/RAM/Disk, recent alerts, recent logs, and fleet trend series. |

## 8. WebSocket (`/ws/metrics`)

Connect to `/ws/metrics?token=<jwt_token>`.

**Client -> Server messages:**
- `{"action": "subscribe", "server_id": "<uuid | all>"}`
- `{"action": "unsubscribe", "server_id": "<uuid | all>"}`
- `{"action": "ping"}`

**Server -> Client messages:**
- `{"type": "connected", "timestamp": "...", "subscriptions": ["all"]}`
- `{"type": "metric_update", "server_id": "...", "server_name": "...", "is_demo": false, "data": { ... }}`
- `{"type": "alert_event", "action": "created|escalated|acknowledged|resolved", "data": { ... }}`
- `{"type": "server_status", "server_id": "...", "status": "healthy|warning|critical|offline", "health_score": 92.5}`
- `{"type": "pong", "timestamp": "..."}`

