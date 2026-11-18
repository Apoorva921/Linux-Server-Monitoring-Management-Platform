#!/usr/bin/env python3
"""
SentinelOps Lightweight Linux Monitoring Agent

Collects real CPU, memory, disk, network (counters + throughput), load average,
uptime, running processes, and approved system logs, transmitting them to the
central SentinelOps FastAPI backend over authenticated HTTP requests.
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

import requests

from collectors.cpu import collect_cpu_metrics
from collectors.disk import collect_disk_metrics
from collectors.logs import LogCollector
from collectors.memory import collect_memory_metrics
from collectors.network import NetworkCollector
from collectors.processes import collect_process_metrics
from collectors.system import collect_host_info, collect_uptime_seconds
from config.settings import AGENT_VERSION, AgentConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | sentinelops-agent | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("sentinelops-agent")


class MonitoringAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.running = True
        self.network_collector = NetworkCollector()
        self.log_collector = LogCollector(
            log_sources=config.log_sources,
            enable_journalctl=config.enable_journalctl,
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Agent-Token": config.api_token,
                "Content-Type": "application/json",
                "User-Agent": f"SentinelOps-Agent/{AGENT_VERSION}",
            }
        )

    def stop(self, *_: Any) -> None:
        logger.info("Shutdown signal received; stopping monitoring agent...")
        self.running = False

    def collect_payload(self) -> Dict[str, Any]:
        cpu = collect_cpu_metrics()
        mem = collect_memory_metrics()
        disk = collect_disk_metrics()
        net = self.network_collector.collect()
        procs = collect_process_metrics(max_processes=self.config.max_processes)
        host_info = collect_host_info()
        uptime = collect_uptime_seconds()

        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **cpu,
            **mem,
            **disk,
            **net,
            **procs,
            "uptime_seconds": uptime,
            "host_info": host_info,
            "is_demo": False,
        }
        if self.config.server_id:
            payload["server_id"] = self.config.server_id
        return payload

    def send_metrics(self, payload: Dict[str, Any]) -> int:
        url = f"{self.config.api_url}/api/metrics/ingest"
        resp = self.session.post(
            url,
            json=payload,
            timeout=self.config.request_timeout_seconds,
            verify=self.config.verify_ssl,
        )
        resp.raise_for_status()
        body = resp.json()
        logger.info(
            "Metrics accepted | status=%s health=%.1f cpu=%.1f%% mem=%.1f%% disk=%.1f%% alerts_triggered=%d",
            body.get("server_status"),
            body.get("health_score", 0.0),
            payload["cpu_percent"],
            payload["memory_percent"],
            payload["disk_percent"],
            body.get("alerts_triggered", 0),
        )
        recommended = int(body.get("recommended_interval_seconds") or self.config.interval_seconds)
        return max(2, min(300, recommended))

    def send_logs(self) -> None:
        entries = self.log_collector.collect()
        if not entries:
            return
        url = f"{self.config.api_url}/api/logs/ingest"
        body: Dict[str, Any] = {"entries": entries, "is_demo": False}
        if self.config.server_id:
            body["server_id"] = self.config.server_id
        resp = self.session.post(
            url,
            json=body,
            timeout=self.config.request_timeout_seconds,
            verify=self.config.verify_ssl,
        )
        resp.raise_for_status()
        logger.info("Ingested %d system log entries", len(entries))

    def run_once(self) -> int:
        payload = self.collect_payload()
        next_interval = self.send_metrics(payload)
        try:
            self.send_logs()
        except Exception as exc:
            logger.warning("Log ingestion warning (metrics unaffected): %s", exc)
        return next_interval

    def run_forever(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        logger.info(
            "Starting SentinelOps Monitoring Agent v%s -> %s (interval=%ds)",
            AGENT_VERSION,
            self.config.api_url,
            self.config.interval_seconds,
        )

        # Warm up network & process counters
        self.network_collector.collect()
        backoff = 2
        interval = self.config.interval_seconds

        while self.running:
            started = time.monotonic()
            try:
                interval = self.run_once()
                backoff = 2
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else "unknown"
                logger.error("Backend rejected request (HTTP %s). Check server ID and API token.", status_code)
                time.sleep(min(60, backoff))
                backoff = min(60, backoff * 2)
                continue
            except requests.RequestException as exc:
                logger.error("Network error contacting backend: %s (retrying in %ds)", exc, backoff)
                time.sleep(min(60, backoff))
                backoff = min(60, backoff * 2)
                continue
            except Exception as exc:
                logger.exception("Unexpected error during collection cycle: %s", exc)
                time.sleep(min(30, backoff))
                backoff = min(30, backoff * 2)
                continue

            elapsed = time.monotonic() - started
            sleep_time = max(0.5, interval - elapsed)
            while self.running and sleep_time > 0:
                step = min(0.5, sleep_time)
                time.sleep(step)
                sleep_time -= step

        logger.info("SentinelOps Monitoring Agent stopped cleanly.")


def main() -> int:
    parser = argparse.ArgumentParser(description="SentinelOps Linux Monitoring Agent")
    parser.add_argument("--once", action="store_true", help="Collect and send a single metric snapshot, then exit.")
    args = parser.parse_args()

    config = AgentConfig()
    try:
        config.validate()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    agent = MonitoringAgent(config)
    if args.once:
        agent.network_collector.collect()
        time.sleep(0.5)
        agent.run_once()
        return 0

    agent.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())

