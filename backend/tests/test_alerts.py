from tests.conftest import sample_metric_payload


def test_alert_threshold_deduplication_escalation_and_recovery(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    token = registered_server["api_token"]

    # 1. Cross CPU warning threshold (default 75%)
    r1 = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=82.0),
    )
    assert r1.status_code == 202
    assert r1.json()["alerts_triggered"] == 1
    assert r1.json()["server_status"] == "warning"

    # 2. Send another interval above warning -> MUST NOT duplicate alert
    r2 = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=84.5),
    )
    assert r2.status_code == 202
    assert r2.json()["alerts_triggered"] == 0

    alerts = client.get("/api/alerts", headers=admin_headers).json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["severity"] == "warning"
    assert alerts["items"][0]["status"] == "active"

    # 3. Escalate above critical threshold (90%) -> upgrades existing alert without duplicate
    r3 = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=95.2),
    )
    assert r3.status_code == 202
    assert r3.json()["alerts_triggered"] == 0
    assert r3.json()["server_status"] == "critical"

    alerts_after_esc = client.get("/api/alerts?severity=critical", headers=admin_headers).json()
    assert alerts_after_esc["total"] == 1
    alert_id = alerts_after_esc["items"][0]["id"]

    # 4. Acknowledge alert
    ack = client.patch(f"/api/alerts/{alert_id}/acknowledge", headers=admin_headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"

    # 5. Recovery: CPU drops back to 35% -> alert auto-resolves
    r4 = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=35.0),
    )
    assert r4.status_code == 202
    assert r4.json()["alerts_resolved"] == 1
    assert r4.json()["server_status"] == "healthy"

    alert_final = client.get(f"/api/alerts/{alert_id}", headers=admin_headers).json()
    assert alert_final["status"] == "resolved"
    assert alert_final["resolved_at"] is not None

    # 6. Cooldown check: immediate spike right after resolution should be suppressed
    r5 = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=88.0),
    )
    assert r5.status_code == 202
    assert r5.json()["alerts_triggered"] == 0


def test_manual_alert_resolve(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    token = registered_server["api_token"]

    client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, memory_percent=93.0),
    )
    alert_id = client.get("/api/alerts", headers=admin_headers).json()["items"][0]["id"]
    res = client.patch(f"/api/alerts/{alert_id}/resolve", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"

