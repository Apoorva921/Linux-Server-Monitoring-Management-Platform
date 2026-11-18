#!/usr/bin/env python3
"""
End-to-end smoke verification script for SentinelOps.
Boots the live FastAPI backend on an ephemeral port, verifies:
  1. Health & admin authentication
  2. Server registration & agent token issuance
  3. Real MonitoringAgent (--once) collecting actual host CPU/RAM/Disk/Network/Processes
  4. DemoSimulator registering 4 clearly labeled [DEMO] hosts & streaming metrics/logs
  5. Dashboard summary accurately distinguishing real data vs DEMO DATA
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
AGENT_DIR = REPO_ROOT / "monitoring-agent"
BACKEND_PY = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
if not BACKEND_PY.exists():
    BACKEND_PY = BACKEND_DIR / ".venv" / "bin" / "python"
if not BACKEND_PY.exists():
    BACKEND_PY = Path(sys.executable)

PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"


def main() -> int:
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    http = requests.Session()
    http.trust_env = False
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_file = Path(tmpdir) / "e2e_verify.db"
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": f"sqlite:///{db_file.as_posix()}",
                "SECRET_KEY": "e2e-verification-secret-key-sentinelops-1234567890",
                "INITIAL_ADMIN_USERNAME": "admin",
                "INITIAL_ADMIN_EMAIL": "admin@sentinelops.io",
                "INITIAL_ADMIN_PASSWORD": "Admin@SentinelOps123!",
                "DISABLE_BACKGROUND_TASKS": "false",
            }
        )

        print("[1/5] Starting live FastAPI backend...")
        server_proc = subprocess.Popen(
            [str(BACKEND_PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            # Wait for /health
            ready = False
            for _ in range(30):
                try:
                    r = http.get(f"{BASE_URL}/health", timeout=2)
                    if r.status_code == 200 and r.json().get("status") == "healthy":
                        ready = True
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.5)

            if not ready:
                server_proc.terminate()
                out, _ = server_proc.communicate(timeout=5)
                print("ERROR: Backend failed to start cleanly.\n--- SERVER OUTPUT ---\n" + out)
                return 1

            print("[2/5] Authenticating admin & registering real host agent...")
            login = http.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "admin", "password": "Admin@SentinelOps123!"},
                timeout=5,
            )
            login.raise_for_status()
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            reg = http.post(
                f"{BASE_URL}/api/servers/register",
                headers=headers,
                json={"hostname": "local-real-host", "display_name": "Local Verified Host"},
                timeout=5,
            )
            reg.raise_for_status()
            reg_data = reg.json()
            server_id = reg_data["server"]["id"]
            agent_token = reg_data["api_token"]

            print("[3/5] Running real monitoring-agent/agent.py --once...")
            agent_env = os.environ.copy()
            agent_env.update(
                {
                    "NO_PROXY": "127.0.0.1,localhost",
                    "no_proxy": "127.0.0.1,localhost",
                    "SENTINELOPS_API_URL": BASE_URL,
                    "SENTINELOPS_SERVER_ID": server_id,
                    "SENTINELOPS_API_TOKEN": agent_token,
                    "SENTINELOPS_ENABLE_JOURNALCTL": "false",
                }
            )
            agent_run = subprocess.run(
                [sys.executable, str(AGENT_DIR / "agent.py"), "--once"],
                cwd=str(AGENT_DIR),
                env=agent_env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if agent_run.returncode != 0:
                print("ERROR: Monitoring agent failed:", agent_run.stdout, agent_run.stderr)
                return 1

            print("[4/5] Running Demo Simulator bootstrap + 1 live cycle...")
            sys.path.insert(0, str(AGENT_DIR))
            from demo_simulator import DemoSimulator

            sim = DemoSimulator(
                api_url=BASE_URL,
                username="admin",
                password="Admin@SentinelOps123!",
                interval=5,
            )
            sim.session.trust_env = False
            sim.authenticate_and_bootstrap_servers()
            sim.run_cycle()

            print("[5/5] Verifying aggregated dashboard summary, real metrics, processes, and logs...")
            summary = http.get(f"{BASE_URL}/api/dashboard/summary", headers=headers, timeout=5).json()
            assert summary["total_servers"] == 5, f"Expected 5 servers (1 real + 4 demo), got {summary['total_servers']}"
            assert summary["online_servers"] == 5
            assert summary["has_real_data"] is True
            assert summary["has_demo_data"] is True

            real_metrics = http.get(f"{BASE_URL}/api/servers/{server_id}/metrics", headers=headers, timeout=5).json()
            assert real_metrics["is_demo"] is False
            assert real_metrics["memory_total_mb"] > 0
            assert real_metrics["disk_total_gb"] > 0

            procs = http.get(f"{BASE_URL}/api/servers/{server_id}/processes", headers=headers, timeout=5).json()
            assert procs["total_processes"] > 0

            logs = http.get(f"{BASE_URL}/api/logs", headers=headers, timeout=5).json()
            assert logs["total"] >= 4

            print(
                f"SUCCESS! Verified end-to-end pipeline: "
                f"{summary['online_servers']}/{summary['total_servers']} servers online "
                f"(real CPU={real_metrics['cpu_percent']}%, RAM={real_metrics['memory_percent']}%, "
                f"Disk={real_metrics['disk_percent']}%, {procs['total_processes']} OS processes, "
                f"{logs['total']} logs ingested)."
            )
            return 0
        finally:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()


if __name__ == "__main__":
    sys.exit(main())
