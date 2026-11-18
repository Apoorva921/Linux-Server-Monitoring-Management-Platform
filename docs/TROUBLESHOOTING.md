# SentinelOps Troubleshooting Guide

## 1. Docker Compose Startup Issues

### PostgreSQL fails health check or port 5432 is already in use
- **Cause**: A local PostgreSQL instance is already bound to port `5432`.
- **Fix**: Change `POSTGRES_PORT` in `.env` or remove the host port mapping in `docker-compose.yml` (backend communicates over the internal Docker network on `postgres:5432`).

### Backend fails to connect to database on startup
- **Cause**: Database container is still initializing.
- **Fix**: `docker-compose.yml` uses `depends_on: postgres: condition: service_healthy`. Inspect logs with `docker compose logs backend` and verify `DATABASE_URL` matches `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.

## 2. Authentication & WebSocket Issues

### WebSocket shows "Disconnected" or reconnects repeatedly
- **Cause 1**: Expired JWT token. **Fix**: Log out and sign in again.
- **Cause 2**: Reverse proxy stripping `Upgrade` / `Connection` headers. **Fix**: Ensure `nginx/nginx.conf` includes `proxy_http_version 1.1`, `proxy_set_header Upgrade $http_upgrade`, and `proxy_set_header Connection "upgrade"`.

### 429 Too Many Requests on `/api/auth/login`
- **Cause**: Auth rate limiter triggered (default 20 requests/minute per client IP).
- **Fix**: Wait 60 seconds or adjust `RATE_LIMIT_AUTH_PER_MINUTE` in `.env`.

## 3. Linux Monitoring Agent Issues

### Agent receives `401 Unauthorized`
- **Cause**: Invalid, revoked, or mismatched `SENTINELOPS_API_TOKEN` or `SENTINELOPS_SERVER_ID`.
- **Fix**: Rotate the token from the Servers page in the dashboard (or `POST /api/servers/{id}/rotate-token`) and update `/etc/sentinelops/agent.env`, then run `sudo systemctl restart sentinelops-agent`.

### Agent cannot read `/var/log/syslog` or `/var/log/auth.log`
- **Cause**: The `sentinelops` service user is not in the `adm` or `systemd-journal` group.
- **Fix**:
  ```bash
  sudo usermod -aG adm,systemd-journal sentinelops
  sudo systemctl restart sentinelops-agent
  ```
  SentinelOps intentionally never attempts to bypass Linux permissions.

### Server shows "Offline" in dashboard
- **Cause**: No metric heartbeat received within `SERVER_OFFLINE_THRESHOLD_SECONDS` (default 30s).
- **Fix**: Check `sudo systemctl status sentinelops-agent` and `journalctl -u sentinelops-agent -n 50` on the monitored host. Verify outbound network connectivity to `SENTINELOPS_API_URL`.

## 4. Demo Mode Notes
- Demo data is explicitly tagged with `is_demo: true` and rendered with a **`DEMO DATA`** badge throughout the dashboard.
- To run without demo data, stop the `demo-simulator` service or omit `--profile demo` when launching Docker Compose.

