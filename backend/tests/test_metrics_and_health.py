from tests.conftest import sample_metric_payload


def test_metric_ingestion_validation_rejects_invalid_ranges(client, registered_server):
    server_id = registered_server["server"]["id"]
    token = registered_server["api_token"]

    bad_cpu = sample_metric_payload(server_id, cpu_percent=145.0)
    res = client.post("/api/metrics/ingest", headers={"X-Agent-Token": token}, json=bad_cpu)
    assert res.status_code == 422
    assert res.json()["error"] == "validation_error"

    bad_mem = sample_metric_payload(server_id, memory_total_mb=0.0)
    res2 = client.post("/api/metrics/ingest", headers={"X-Agent-Token": token}, json=bad_mem)
    assert res2.status_code == 422


def test_metric_ingestion_history_processes_and_health_score(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    token = registered_server["api_token"]

    res1 = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=28.0, memory_percent=42.0, disk_percent=50.0),
    )
    assert res1.status_code == 202
    body1 = res1.json()
    assert body1["server_status"] == "healthy"
    assert body1["health_score"] == 100.0

    # Latest metrics endpoint
    latest = client.get(f"/api/servers/{server_id}/metrics", headers=admin_headers)
    assert latest.status_code == 200
    assert latest.json()["cpu_percent"] == 28.0
    assert latest.json()["net_upload_bps"] == 1048576.0

    # History endpoint
    history = client.get(f"/api/servers/{server_id}/metrics/history?range=1h", headers=admin_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1

    # Processes endpoint with sorting and search
    procs = client.get(
        f"/api/servers/{server_id}/processes?sort_by=cpu_percent&order=desc",
        headers=admin_headers,
    )
    assert procs.status_code == 200
    plist = procs.json()["processes"]
    assert len(plist) == 2
    assert plist[0]["name"] == "postgres"

    procs_filtered = client.get(
        f"/api/servers/{server_id}/processes?search=nginx",
        headers=admin_headers,
    )
    assert len(procs_filtered.json()["processes"]) == 1
    assert procs_filtered.json()["processes"][0]["pid"] == 1024

    # Server detail shows transparent health explanation
    srv = client.get(f"/api/servers/{server_id}", headers=admin_headers).json()
    assert srv["health_score"] == 100.0
    assert "healthy operating ranges" in srv["health_explanation"]["summary"]

