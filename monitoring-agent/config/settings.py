import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

AGENT_VERSION = "1.0.0"


@dataclass
class AgentConfig:
    api_url: str = field(default_factory=lambda: os.getenv("SENTINELOPS_API_URL", "http://localhost:8000").rstrip("/"))
    server_id: str = field(default_factory=lambda: os.getenv("SENTINELOPS_SERVER_ID", "").strip())
    api_token: str = field(default_factory=lambda: os.getenv("SENTINELOPS_API_TOKEN", "").strip())
    interval_seconds: int = field(
        default_factory=lambda: max(2, int(os.getenv("SENTINELOPS_INTERVAL_SECONDS", "5")))
    )
    request_timeout_seconds: int = field(
        default_factory=lambda: max(3, int(os.getenv("SENTINELOPS_TIMEOUT_SECONDS", "10")))
    )
    log_sources: List[str] = field(
        default_factory=lambda: [
            p.strip()
            for p in os.getenv("SENTINELOPS_LOG_SOURCES", "/var/log/syslog,/var/log/auth.log").split(",")
            if p.strip()
        ]
    )
    enable_journalctl: bool = field(
        default_factory=lambda: os.getenv("SENTINELOPS_ENABLE_JOURNALCTL", "true").lower() in ("1", "true", "yes")
    )
    max_processes: int = field(
        default_factory=lambda: max(5, min(100, int(os.getenv("SENTINELOPS_MAX_PROCESSES", "30"))))
    )
    verify_ssl: bool = field(
        default_factory=lambda: os.getenv("SENTINELOPS_VERIFY_SSL", "true").lower() not in ("0", "false", "no")
    )

    def validate(self) -> None:
        if not self.api_token:
            raise ValueError("SENTINELOPS_API_TOKEN is required.")
        if not self.api_token.startswith("sops_"):
            raise ValueError("SENTINELOPS_API_TOKEN must start with 'sops_'.")
        if not self.api_url.startswith(("http://", "https://")):
            raise ValueError("SENTINELOPS_API_URL must be an http:// or https:// URL.")
