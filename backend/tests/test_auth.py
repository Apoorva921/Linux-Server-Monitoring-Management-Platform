def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"


def test_admin_login_and_me(client):
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    data = login.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"
    assert "hashed_password" not in data["user"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_register_viewer_and_rbac_enforcement(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "username": "operator1",
            "email": "operator1@sentinelops.io",
            "password": "StrongPassword99!",
            "full_name": "Viewer User",
            "role": "admin",  # Public registration must downgrade to viewer
        },
    )
    assert reg.status_code == 201
    assert reg.json()["role"] == "viewer"

    login = client.post(
        "/api/auth/login",
        json={"username": "operator1", "password": "StrongPassword99!"},
    )
    assert login.status_code == 200
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Viewer can read servers
    assert client.get("/api/servers", headers=viewer_headers).status_code == 200
    # Viewer cannot register a server (admin only)
    forbidden = client.post(
        "/api/servers/register",
        headers=viewer_headers,
        json={"hostname": "unauth-host"},
    )
    assert forbidden.status_code == 403


def test_invalid_login_rejected(client):
    res = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert res.json()["error"] == "invalid_credentials"
