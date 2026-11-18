from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ServerRegisterRequest(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    ip_address: str = Field(default="0.0.0.0", max_length=64)
    os_name: str = Field(default="Ubuntu Linux", max_length=128)
    os_version: str = Field(default="24.04 LTS", max_length=128)
    kernel_version: str = Field(default="Unknown", max_length=128)
    architecture: str = Field(default="x86_64", max_length=64)
    cpu_cores: int = Field(default=1, ge=1, le=2048)
    total_memory_mb: float = Field(default=0.0, ge=0.0)
    total_disk_gb: float = Field(default=0.0, ge=0.0)
    agent_version: str = Field(default="1.0.0", max_length=32)
    is_demo: bool = False
    tags: List[str] = Field(default_factory=list, max_length=20)


class HealthDeduction(BaseModel):
    factor: str
    value: str
    impact: float
    reason: str


class HealthExplanation(BaseModel):
    score: float
    status: str
    summary: str
    deductions: List[HealthDeduction] = Field(default_factory=list)


class ServerMetricBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    net_upload_bps: float
    net_download_bps: float
    net_bytes_sent: int
    net_bytes_recv: int
    net_packets_sent: int
    net_packets_recv: int
    net_interface: str
    load_1m: float
    load_5m: float
    load_15m: float
    uptime_seconds: int
    process_count: int


class ServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hostname: str
    display_name: str
    ip_address: str
    os_name: str
    os_version: str
    kernel_version: str
    architecture: str
    cpu_cores: int
    total_memory_mb: float
    total_disk_gb: float
    agent_version: str
    status: str
    health_score: float
    health_explanation: Optional[Dict[str, Any]] = None
    uptime_seconds: int
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    last_heartbeat: Optional[datetime] = None
    is_demo: bool
    tags: List[str]
    created_at: datetime
    latest_metric: Optional[ServerMetricBrief] = None
    active_alert_count: int = 0


class ServerRegisterResponse(BaseModel):
    server: ServerResponse
    api_token: str
    token_prefix: str
    warning: str = "Store this API token securely now. It will not be displayed again."


class TokenRotateResponse(BaseModel):
    server_id: str
    api_token: str
    token_prefix: str
    warning: str = "Previous agent tokens have been revoked. Store this token securely now."

