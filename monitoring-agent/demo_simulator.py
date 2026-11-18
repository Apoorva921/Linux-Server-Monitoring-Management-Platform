#!/usr/bin/env python3
"""
SentinelOps Demo Mode Simulator

Simulates multiple Linux servers with realistic workloads, periodic threshold spikes,
recoveries, process lists, and syslog/auth.log events. All simulated records are
explicitly flagged with `is_demo=True` and labeled `[DEMO]` so they are never
mistaken for real production servers.
"""

import logging
import math
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | sentinelops-demo | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("sentinelops-demo")


@dataclass
class SimulatedServerProfile:
    hostname: str
    display_name: str
    ip_address: str
    os_name: str
    os_version: str
    kernel_version: str
    cpu_cores: int
    total_memory_mb: float
    total_disk_gb: float
    base_cpu: float
    base_mem: float
    base_disk: float
    base_net_mbps: float
    processes: List[Dict[str, object]]
    tags: List[str]
    server_id: str = ""
    api_token: str = ""
    bytes_sent: int = field(default_factory=lambda: random.randint(2_000_000_000, 15_000_000_000))
    bytes_recv: int = field(default_factory=lambda: random.randint(4_000_000_000, 30_000_000_000))
    packets_sent: int = field(default_factory=lambda: random.randint(5_000_000, 25_000_000))
    packets_recv: int = field(default_factory=lambda: random.randint(8_000_000, 40_000_000))
    uptime_seconds: int = field(default_factory=lambda: random.randint(86_400, 2_592_000))
    spike_ticks_remaining: int = 0
    spike_type: str = "cpu"


SIMULATED_PROFILES = [
    SimulatedServerProfile(
        hostname="prod-web-01.demo.internal",
        display_name="prod-web-01 [DEMO]",
        ip_address="10.20.1.11",
        os_name="Ubuntu",
        os_version="24.04.1 LTS",
        kernel_version="6.8.0-45-generic",
        cpu_cores=8,
        total_memory_mb=16384.0,
        total_disk_gb=250.0,
        base_cpu=38.0,
        base_mem=54.0,
        base_disk=46.0,
        base_net_mbps=14.0,
        tags=["demo", "web", "nginx", "us-east-1"],
        processes=[
            {"pid": 1102, "name": "nginx", "username": "www-data", "status": "running"},
            {"pid": 1488, "name": "uvicorn", "username": "appuser", "status": "running"},
            {"pid": 1492, "name": "gunicorn", "username": "appuser", "status": "sleeping"},
            {"pid": 820, "name": "node_exporter", "username": "prometheus", "status": "sleeping"},
            {"pid": 412, "name": "systemd-journald", "username": "root", "status": "sleeping"},
            {"pid": 621, "name": "sshd", "username": "root", "status": "sleeping"},
        ],
    ),
    SimulatedServerProfile(
        hostname="prod-db-01.demo.internal",
        display_name="prod-db-01 [DEMO]",
        ip_address="10.20.2.21",
        os_name="Ubuntu",
        os_version="22.04.5 LTS",
        kernel_version="5.15.0-119-generic",
        cpu_cores=16,
        total_memory_mb=65536.0,
        total_disk_gb=1000.0,
        base_cpu=52.0,
        base_mem=71.0,
        base_disk=74.0,
        base_net_mbps=22.0,
        tags=["demo", "postgresql", "primary-db", "us-east-1"],
        processes=[
            {"pid": 2041, "name": "postgres", "username": "postgres", "status": "running"},
            {"pid": 2049, "name": "postgres: walwriter", "username": "postgres", "status": "sleeping"},
            {"pid": 2054, "name": "pgbouncer", "username": "postgres", "status": "running"},
            {"pid": 910, "name": "rsyslogd", "username": "syslog", "status": "sleeping"},
            {"pid": 511, "name": "cron", "username": "root", "status": "sleeping"},
        ],
    ),
    SimulatedServerProfile(
        hostname="worker-batch-02.demo.internal",
        display_name="worker-batch-02 [DEMO]",
        ip_address="10.20.3.34",
        os_name="Ubuntu",
        os_version="24.04.1 LTS",
        kernel_version="6.8.0-45-generic",
        cpu_cores=12,
        total_memory_mb=32768.0,
        total_disk_gb=500.0,
        base_cpu=61.0,
        base_mem=63.0,
        base_disk=58.0,
        base_net_mbps=9.5,
        tags=["demo", "celery", "worker", "eu-west-1"],
        processes=[
            {"pid": 3120, "name": "celery", "username": "worker", "status": "running"},
            {"pid": 3145, "name": "python3", "username": "worker", "status": "running"},
            {"pid": 1820, "name": "redis-server", "username": "redis", "status": "sleeping"},
            {"pid": 774, "name": "dockerd", "username": "root", "status": "sleeping"},
            {"pid": 612, "name": "containerd", "username": "root", "status": "sleeping"},
        ],
    ),
    SimulatedServerProfile(
        hostname="edge-cache-03.demo.internal",
        display_name="edge-cache-03 [DEMO]",
        ip_address="10.20.4.48",
        os_name="Debian GNU/Linux",
        os_version="12 (bookworm)",
        kernel_version="6.1.0-25-amd64",
        cpu_cores=4,
        total_memory_mb=8192.0,
        total_disk_gb=120.0,
        base_cpu=24.0,
        base_mem=44.0,
        base_disk=33.0,
        base_net_mbps=31.0,
        tags=["demo", "redis", "edge", "ap-south-1"],
        processes=[
            {"pid": 1340, "name": "varnishd", "username": "varnish", "status": "running"},
            {"pid": 1522, "name": "redis-server", "username": "redis", "status": "running"},
            {"pid": 811, "name": "haproxy", "username": "haproxy", "status": "running"},
            {"pid": 402, "name": "sshd", "username": "root", "status": "sleeping"},
        ],
    ),
]

DEMO_LOG_TEMPLATES = [
    ("INFO", "systemd", "[DEMO DATA] Completed scheduled logrotate health check."),
    ("INFO", "nginx", "[DEMO DATA] Upstream health probe succeeded in 4ms (200 OK)."),
    ("INFO", "postgres", "[DEMO DATA] Checkpoint complete: wrote 412 buffers (2.5%); 0 WAL files added."),
    ("WARNING", "auth.log", "[DEMO DATA] Failed password for invalid user admin from 203.0.113.42 port 51822 ssh2"),
    ("WARNING", "kernel", "[DEMO DATA] TCP: eth0: possible SYN flooding or burst traffic detected."),
    ("ERROR", "uvicorn", "[DEMO DATA] Connection pool wait time exceeded 1500ms during traffic burst."),
    ("ERROR", "systemd", "[DEMO DATA] Transient worker job exited with status 1; automatic restart triggered."),
    ("CRITICAL", "kernel", "[DEMO DATA] High CPU/memory contention warning emitted by cgroup watchdog."),
]


class DemoSimulator:
    def __init__(self, api_url: str, username: str, password: str, interval: int = 5) -> None:
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        self.interval = max(2, interval)
        self.running = True
        self.tick = 0
        self.session = requests.Session()

    def stop(self, *_) -> None:
        logger.info("Stopping Demo Simulator...")
        self.running = False

    def wait_for_backend(self) -> None:
        while self.running:
            try:
                r = self.session.get(f"{self.api_url}/health", timeout=5)
                if r.status_code == 200:
                    logger.info("Connected to SentinelOps backend at %s", self.api_url)
                    return
            except requests.RequestException:
                pass
            logger.info("Waiting for backend at %s/health...", self.api_url)
            time.sleep(2)

    def authenticate_and_bootstrap_servers(self) -> None:
        login = self.session.post(
            f"{self.api_url}/api/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=10,
        )
        login.raise_for_status()
        jwt_token = login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {jwt_token}"}

        existing = self.session.get(
            f"{self.api_url}/api/servers?is_demo=true&page_size=100",
            headers=admin_headers,
            timeout=10,
        )
        existing.raise_for_status()
        by_hostname = {s["hostname"]: s for s in existing.json()["items"]}

        for profile in SIMULATED_PROFILES:
            if profile.hostname in by_hostname:
                srv = by_hostname[profile.hostname]
                profile.server_id = srv["id"]
                rot = self.session.post(
                    f"{self.api_url}/api/servers/{profile.server_id}/rotate-token",
                    headers=admin_headers,
                    timeout=10,
                )
                rot.raise_for_status()
                profile.api_token = rot.json()["api_token"]
                logger.info("Reattached demo server %s (%s)", profile.display_name, profile.server_id)
            else:
                reg = self.session.post(
                    f"{self.api_url}/api/servers/register",
                    headers=admin_headers,
                    json={
                        "hostname": profile.hostname,
                        "display_name": profile.display_name,
                        "ip_address": profile.ip_address,
                        "os_name": profile.os_name,
                        "os_version": profile.os_version,
                        "kernel_version": profile.kernel_version,
                        "architecture": "x86_64",
                        "cpu_cores": profile.cpu_cores,
                        "total_memory_mb": profile.total_memory_mb,
                        "total_disk_gb": profile.total_disk_gb,
                        "agent_version": "1.0.0-demo",
                        "is_demo": True,
                        "tags": profile.tags,
                    },
                    timeout=10,
                )
                reg.raise_for_status()
                data = reg.json()
                profile.server_id = data["server"]["id"]
                profile.api_token = data["api_token"]
                logger.info("Registered demo server %s (%s)", profile.display_name, profile.server_id)

    def _build_metric(self, p: SimulatedServerProfile, idx: int) -> Dict[str, object]:
        wave = math.sin((self.tick + idx * 7) / 6.0)

        # Occasionally inject realistic threshold spikes that recover cleanly
        if p.spike_ticks_remaining <= 0 and random.random() < 0.08:
            p.spike_ticks_remaining = random.randint(3, 6)
            p.spike_type = random.choice(["cpu", "memory", "cpu"])

        cpu_boost = 0.0
        mem_boost = 0.0
        if p.spike_ticks_remaining > 0:
            p.spike_ticks_remaining -= 1
            if p.spike_type == "cpu":
                cpu_boost = random.uniform(28.0, 42.0)
            else:
                mem_boost = random.uniform(16.0, 26.0)

        cpu = max(3.0, min(98.5, p.base_cpu + wave * 12.0 + random.uniform(-4.0, 4.0) + cpu_boost))
        mem = max(15.0, min(96.5, p.base_mem + wave * 5.0 + random.uniform(-2.0, 2.0) + mem_boost))
        disk = max(10.0, min(94.0, p.base_disk + (self.tick % 40) * 0.04 + random.uniform(-0.2, 0.3)))

        upload_bps = max(50_000.0, (p.base_net_mbps * 0.45 + abs(wave) * 6.0 + random.uniform(-2, 3)) * 1_048_576)
        download_bps = max(100_000.0, (p.base_net_mbps * 0.85 + abs(wave) * 10.0 + random.uniform(-3, 5)) * 1_048_576)

        p.bytes_sent += int(upload_bps * self.interval)
        p.bytes_recv += int(download_bps * self.interval)
        p.packets_sent += int(upload_bps * self.interval / 1100)
        p.packets_recv += int(download_bps * self.interval / 1100)
        p.uptime_seconds += self.interval

        mem_used = round(p.total_memory_mb * (mem / 100.0), 2)
        mem_avail = round(max(0.0, p.total_memory_mb - mem_used), 2)
        disk_used = round(p.total_disk_gb * (disk / 100.0), 2)
        disk_free = round(max(0.0, p.total_disk_gb - disk_used), 2)

        procs = []
        remaining_cpu = cpu
        for i, base_proc in enumerate(p.processes):
            share = max(0.3, remaining_cpu * (0.45 if i == 0 else 0.25) + random.uniform(-1.5, 2.5))
            remaining_cpu = max(1.0, remaining_cpu - share * 0.6)
            procs.append(
                {
                    **base_proc,
                    "cpu_percent": round(min(99.0, share), 2),
                    "memory_percent": round(max(0.4, (mem / len(p.processes)) * (1.6 if i == 0 else 0.7)), 2),
                }
            )
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)

        load_base = round((cpu / 100.0) * p.cpu_cores * 0.85, 2)
        return {
            "server_id": p.server_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": round(cpu, 2),
            "cpu_user": round(cpu * 0.72, 2),
            "cpu_system": round(cpu * 0.22, 2),
            "cpu_iowait": round(cpu * 0.06, 2),
            "memory_percent": round(mem, 2),
            "memory_used_mb": mem_used,
            "memory_available_mb": mem_avail,
            "memory_total_mb": p.total_memory_mb,
            "swap_percent": round(max(0.0, (mem - 65.0) * 0.4), 2),
            "disk_percent": round(disk, 2),
            "disk_used_gb": disk_used,
            "disk_total_gb": p.total_disk_gb,
            "disk_partitions": [
                {
                    "device": "/dev/nvme0n1p1",
                    "mountpoint": "/",
                    "fstype": "ext4",
                    "total_gb": round(p.total_disk_gb * 0.7, 2),
                    "used_gb": round(disk_used * 0.72, 2),
                    "free_gb": round(max(0.0, p.total_disk_gb * 0.7 - disk_used * 0.72), 2),
                    "percent": round(min(99.0, disk * 1.02), 2),
                },
                {
                    "device": "/dev/nvme0n1p2",
                    "mountpoint": "/var/lib/data",
                    "fstype": "xfs",
                    "total_gb": round(p.total_disk_gb * 0.3, 2),
                    "used_gb": round(disk_used * 0.28, 2),
                    "free_gb": round(max(0.0, p.total_disk_gb * 0.3 - disk_used * 0.28), 2),
                    "percent": round(max(5.0, disk * 0.93), 2),
                },
            ],
            "net_bytes_sent": p.bytes_sent,
            "net_bytes_recv": p.bytes_recv,
            "net_packets_sent": p.packets_sent,
            "net_packets_recv": p.packets_recv,
            "net_interface": "eth0",
            "net_upload_bps": round(upload_bps, 2),
            "net_download_bps": round(download_bps, 2),
            "load_1m": load_base,
            "load_5m": round(load_base * 0.92, 2),
            "load_15m": round(load_base * 0.85, 2),
            "uptime_seconds": p.uptime_seconds,
            "process_count": 115 + idx * 24 + random.randint(-5, 8),
            "top_processes": procs,
            "is_demo": True,
        }

    def run_cycle(self) -> None:
        self.tick += 1
        for idx, profile in enumerate(SIMULATED_PROFILES):
            metric_payload = self._build_metric(profile, idx)
            r = self.session.post(
                f"{self.api_url}/api/metrics/ingest",
                headers={"X-Agent-Token": profile.api_token},
                json=metric_payload,
                timeout=10,
            )
            r.raise_for_status()

            # Periodically push realistic demo log events
            if self.tick == 1 or random.random() < 0.35:
                sev, src, msg = random.choice(DEMO_LOG_TEMPLATES)
                self.session.post(
                    f"{self.api_url}/api/logs/ingest",
                    headers={"X-Agent-Token": profile.api_token},
                    json={
                        "server_id": profile.server_id,
                        "is_demo": True,
                        "entries": [
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "severity": sev,
                                "source": src,
                                "hostname": profile.hostname,
                                "message": msg,
                                "raw_line": f"{datetime.now(timezone.utc).isoformat()} {profile.hostname} {src}: {msg}",
                            }
                        ],
                    },
                    timeout=10,
                )

    def run_forever(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self.wait_for_backend()
        if not self.running:
            return
        self.authenticate_and_bootstrap_servers()
        logger.info("Demo Simulator streaming DEMO DATA for %d servers every %ds", len(SIMULATED_PROFILES), self.interval)

        while self.running:
            started = time.monotonic()
            try:
                self.run_cycle()
            except Exception as exc:
                logger.error("Demo cycle error: %s", exc)
                time.sleep(5)
                continue
            elapsed = time.monotonic() - started
            sleep_for = max(0.5, self.interval - elapsed)
            while self.running and sleep_for > 0:
                step = min(0.5, sleep_for)
                time.sleep(step)
                sleep_for -= step


def main() -> int:
    api_url = os.getenv("DEMO_API_URL", "http://localhost:8000")
    username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "Admin@SentinelOps123!")
    interval = int(os.getenv("DEMO_INTERVAL_SECONDS", "5"))

    sim = DemoSimulator(api_url=api_url, username=username, password=password, interval=interval)
    sim.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())

