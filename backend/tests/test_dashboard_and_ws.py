from starlette.websockets import WebSocketDisconnect
import pytest

from tests.conftest import sample_metric_payload


def test_dashboard_summary_aggregates_real_data(client, admin_headers, registered_server):
    server_id = registered_server["server"]["id"]
    token = registered_server["api_token"]

    client.post(
        "/api/metrics/ingest",
        headers={"X-Agent-Token": token},
        json=sample_metric_payload(server_id, cpu_percent=40.0, memory_percent=50.0, disk_percent=60.0),
    )

    res = client.get("/api/dashboard/summary", headers=admin_headers)
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_servers"] == 1
    assert summary["online_servers"] == 1
    assert summary["healthy_servers"] == 1
    assert summary["avg_cpu_percent"] == 40.0
    assert summary["avg_memory_percent"] == 50.0
    assert summary["avg_disk_percent"] == 60.0
    assert summary["has_real_data"] is True
    assert summary["has_demo_data"] is False
    assert len(summary["trend_series"]) >= 1


def test_websocket_auth_and_live_metric_broadcast(client, admin_token, registered_server):
    server_id = registered_server["server"]["id"]
    agent_token = registered_server["api_token"]

    # Unauthenticated WS rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/metrics?token=invalid.jwt.token") as ws:
            ws.receive_json()

    # Authenticated WS receives connected ack, ping/pong, and real-time metric_update
    with client.websocket_connect(f"/ws/metrics?token={admin_token}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connected"

        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"

        ws.send_json({"action": "subscribe", "server_id": server_id})
        sub = ws.receive_json()
        assert sub["type"] == "subscribed"
        assert server_id in sub["subscriptions"]

        # Ingest metric while WS is open -> live event pushed immediately
        ingest = client.post(
            "/api/metrics/ingest",
            headers={"X-Agent-Token": agent_token},
            json=sample_metric_payload(server_id, cpu_percent=55.5),
        )
        assert ingest.status_code == 202

        event = ws.receive_json()
        assert event["type"] == "metric_update"
        assert event["server_id"] == server_id
        assert event["data"]["cpu_percent"] == 55.5

