def test_log_ingestion_and_filtering(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    token = registered_server["api_token"]

    ingest = client.post(
        "/api/logs/ingest",
        headers={"X-Agent-Token": token},
        json={
            "server_id": server_id,
            "entries": [
                {
                    "severity": "INFO",
                    "source": "systemd",
                    "message": "Started nginx web server successfully",
                },
                {
                    "severity": "WARNING",
                    "source": "auth.log",
                    "message": "Failed password for invalid user root from 192.168.1.50",
                },
                {
                    "severity": "ERROR",
                    "source": "kernel",
                    "message": "Out of memory: Killed process 4412 (python3)",
                },
            ],
        },
    )
    assert ingest.status_code == 202
    assert ingest.json()["ingested_count"] == 3

    all_logs = client.get("/api/logs", headers=admin_headers).json()
    assert all_logs["total"] == 3

    error_logs = client.get("/api/logs?severity=ERROR", headers=admin_headers).json()
    assert error_logs["total"] == 1
    assert "Out of memory" in error_logs["items"][0]["message"]

    search = client.get("/api/logs/search?q=Failed%20password", headers=admin_headers).json()
    assert search["total"] == 1
    assert search["items"][0]["source"] == "auth.log"


def test_settings_get_and_update(client, admin_headers):
    res = client.get("/api/settings", headers=admin_headers)
    assert res.status_code == 200
    current = res.json()
    assert current["monitoring_interval_seconds"] == 5
    assert len(current["thresholds"]) >= 5

    # Update CPU thresholds & interval
    updated_thresholds = current["thresholds"]
    for t in updated_thresholds:
        if t["metric_type"] == "cpu":
            t["warning_threshold"] = 70.0
            t["critical_threshold"] = 85.0

    put = client.put(
        "/api/settings",
        headers=admin_headers,
        json={
            "monitoring_interval_seconds": 10,
            "offline_threshold_seconds": 45,
            "metric_retention_days": 14,
            "log_sources": ["/var/log/syslog", "/var/log/auth.log"],
            "enable_journalctl": True,
            "max_processes_per_snapshot": 25,
            "thresholds": updated_thresholds,
        },
    )
    assert put.status_code == 200
    body = put.json()
    assert body["monitoring_interval_seconds"] == 10
    assert body["metric_retention_days"] == 14
    cpu_rule = next(t for t in body["thresholds"] if t["metric_type"] == "cpu")
    assert cpu_rule["warning_threshold"] == 70.0
    assert cpu_rule["critical_threshold"] == 85.0

