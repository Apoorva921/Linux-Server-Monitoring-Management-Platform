from tests.conftest import sample_metric_payload


def test_server_registration_and_listing(client, admin_headers, registered_server):
    assert registered_server["api_token"].startswith("sops_")
    server_id = registered_server["server"]["id"]
    assert registered_server["server"]["status"] == "offline"

    listing = client.get("/api/servers", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == server_id

    detail = client.get(f"/api/servers/{server_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["hostname"] == "ubuntu-prod-01"


def test_agent_token_authentication_and_rotation(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    old_token = registered_server["api_token"]

    # Missing token rejected
    res_missing = client.post("/api/metrics/ingest", json=sample_metric_payload(server_id))
    assert res_missing.status_code == 401

    # Invalid token rejected
    res_bad = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": "sops_invalid_token_value"},
        json=sample_metric_payload(server_id),
    )
    assert res_bad.status_code == 401

    # Mismatched server_id rejected
    res_mismatch = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": old_token},
        json=sample_metric_payload("00000000-0000-0000-0000-000000000000"),
    )
    assert res_mismatch.status_code == 403

    # Valid token accepted
    res_ok = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": old_token},
        json=sample_metric_payload(server_id),
    )
    assert res_ok.status_code == 202

    # Rotate token -> old token immediately revoked, new token works
    rot = client.post(f"/api/servers/{server_id}/rotate-token", headers=admin_headers)
    assert rot.status_code == 200
    new_token = rot.json()["api_token"]
    assert new_token != old_token

    res_old = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": old_token},
        json=sample_metric_payload(server_id),
    )
    assert res_old.status_code == 401

    res_new = client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": new_token},
        json=sample_metric_payload(server_id),
    )
    assert res_new.status_code == 202


def test_delete_server(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    res = client.delete(f"/api/servers/{server_id}", headers=admin_headers)
    assert res.status_code == 200
    assert client.get(f"/api/servers/{server_id}", headers=admin_headers).status_code == 404

