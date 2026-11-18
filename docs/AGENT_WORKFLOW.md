# SentinelOps Monitoring Agent Workflow

## Agent Lifecycle & Collection Pipeline

```mermaid
sequenceDiagram
    participant Admin as Administrator
    participant API as SentinelOps Backend
    participant Host as Linux Server (Agent)
    participant DB as PostgreSQL
    participant UI as Web Dashboard

    Admin->>API: POST /api/servers/register
    API->>DB: Insert Server + Hashed Agent Token
    API-->>Admin: Return server_id + one-time API token (sops_...)

    Admin->>Host: Configure .env / systemd service with server_id & token
    Host->>Host: Start monitoring agent (non-root user)

    loop Every N seconds (default 5s)
        Host->>Host: Collect CPU, RAM, Disk, Net Counters + Delta Throughput
        Host->>Host: Collect Load Avg, Uptime, Top Processes
        Host->>API: POST /api/metrics/ingest (X-Agent-Token)
        API->>API: Verify Token HMAC & Validate Pydantic Payload
        API->>DB: Store server_metrics & update server heartbeat
        API->>API: Evaluate Alert Rules (Dedup + Cooldown + Recovery)
        API->>API: Compute Transparent Health Score (0-100)
        API-->>UI: WebSocket Broadcast (metric_update + alert_event)
        API-->>Host: 202 Accepted (next interval hint)

        opt New entries in /var/log/syslog, auth.log, or journalctl
            Host->>Host: Tail new lines (track inode + byte offset) & parse
            Host->>API: POST /api/logs/ingest (X-Agent-Token)
            API->>DB: Bulk insert system_logs
        end
    end
```

## Security Principles

1. **Least Privilege**: Runs under dedicated `sentinelops` Linux user with read-only membership in `adm` and `systemd-journal`. Never runs as `root`.
2. **No Remote Command Execution**: The agent is strictly push-only (outbound HTTPS/HTTP POST). It opens zero listening ports and executes no user-supplied shell commands.
3. **Graceful Degradation**: If `/var/log/auth.log` or `journalctl` is unreadable due to OS permissions, the agent logs a warning once and continues collecting metrics without attempting privilege escalation.
4. **Retry & Backoff**: Transient network errors trigger exponential backoff up to 60 seconds without crashing the agent daemon.

