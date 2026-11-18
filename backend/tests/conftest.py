import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend/ is importable
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-sentinelops-pytest-suite-123456"
os.environ["DISABLE_BACKGROUND_TASKS"] = "true"
os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
os.environ["INITIAL_ADMIN_EMAIL"] = "admin@sentinelops.test"
os.environ["INITIAL_ADMIN_PASSWORD"] = "AdminPass123!"

from app.core.config import get_settings  # noqa: E402
from app.core.rate_limiter import auth_rate_limiter  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.init_db import seed_initial_data  # noqa: E402
from app.database.session import get_db  # noqa: E402
import app.database.session as db_session_module  # noqa: E402
import app.main as main_module  # noqa: E402

get_settings.cache_clear()


@pytest.fixture()
def db_session():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False
    )
    Base.metadata.create_all(bind=test_engine)

    # Patch global engine / session factory used by lifespan & health check
    db_session_module.engine = test_engine
    db_session_module.SessionLocal = TestingSessionLocal
    main_module.engine = test_engine
    main_module.SessionLocal = TestingSessionLocal

    session = TestingSessionLocal()
    seed_initial_data(session)
    try:
        yield session, TestingSessionLocal
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture()
def client(db_session):
    _, session_factory = db_session
    auth_rate_limiter.reset()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    main_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers(client):
    res = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_token(client):
    res = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture()
def registered_server(client, admin_headers):
    res = client.post(
        "/api/servers/register",
        headers=admin_headers,
        json={
            "hostname": "ubuntu-prod-01",
            "display_name": "Ubuntu Prod 01",
            "ip_address": "10.0.1.15",
            "os_name": "Ubuntu",
            "os_version": "24.04 LTS",
            "cpu_cores": 8,
            "total_memory_mb": 16384.0,
            "total_disk_gb": 250.0,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def sample_metric_payload(server_id: str | None = None, **overrides):
    base = {
        "server_id": server_id,
        "cpu_percent": 32.5,
        "cpu_user": 24.0,
        "cpu_system": 7.5,
        "cpu_iowait": 1.0,
        "memory_percent": 48.0,
        "memory_used_mb": 7864.0,
        "memory_available_mb": 8520.0,
        "memory_total_mb": 16384.0,
        "swap_percent": 2.5,
        "disk_percent": 55.0,
        "disk_used_gb": 137.5,
        "disk_total_gb": 250.0,
        "disk_partitions": [
            {
                "device": "/dev/sda1",
                "mountpoint": "/",
                "fstype": "ext4",
                "total_gb": 250.0,
                "used_gb": 137.5,
                "free_gb": 112.5,
                "percent": 55.0,
            }
        ],
        "net_bytes_sent": 104857600,
        "net_bytes_recv": 209715200,
        "net_packets_sent": 150000,
        "net_packets_recv": 280000,
        "net_interface": "eth0",
        "net_upload_bps": 1048576.0,
        "net_download_bps": 4194304.0,
        "load_1m": 1.25,
        "load_5m": 1.10,
        "load_15m": 0.95,
        "uptime_seconds": 864000,
        "process_count": 142,
        "top_processes": [
            {
                "pid": 1024,
                "name": "nginx",
                "cpu_percent": 12.4,
                "memory_percent": 3.2,
                "username": "www-data",
                "status": "running",
            },
            {
                "pid": 2048,
                "name": "postgres",
                "cpu_percent": 18.7,
                "memory_percent": 19.5,
                "username": "postgres",
                "status": "sleeping",
            },
        ],
    }
    base.update(overrides)
    return base

