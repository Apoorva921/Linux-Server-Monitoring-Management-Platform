from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DiskPartitionSchema(BaseModel):
    device: str = Field(..., max_length=128)
    mountpoint: str = Field(..., max_length=255)
    fstype: str = Field(default="ext4", max_length=64)
    total_gb: float = Field(..., ge=0.0)
    used_gb: float = Field(..., ge=0.0)
    free_gb: float = Field(..., ge=0.0)
    percent: float = Field(..., ge=0.0, le=100.0)


class ProcessInfoSchema(BaseModel):
    pid: int = Field(..., ge=0)
    name: str = Field(..., max_length=255)
    cpu_percent: float = Field(..., ge=0.0)
    memory_percent: float = Field(..., ge=0.0, le=100.0)
    username: str = Field(default="unknown", max_length=128)
    status: str = Field(default="running", max_length=64)


class HostInfoSchema(BaseModel):
    hostname: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    os_name: Optional[str] = Field(default=None, max_length=128)
    os_version: Optional[str] = Field(default=None, max_length=128)
    kernel_version: Optional[str] = Field(default=None, max_length=128)
    architecture: Optional[str] = Field(default=None, max_length=64)
    cpu_cores: Optional[int] = Field(default=None, ge=1, le=2048)
    agent_version: Optional[str] = Field(default=None, max_length=32)


class MetricIngestRequest(BaseModel):
    server_id: Optional[str] = Field(default=None, max_length=36)
    timestamp: Optional[datetime] = None

    # CPU
    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    cpu_user: float = Field(default=0.0, ge=0.0, le=100.0)
    cpu_system: float = Field(default=0.0, ge=0.0, le=100.0)
    cpu_iowait: float = Field(default=0.0, ge=0.0, le=100.0)

    # Memory
    memory_percent: float = Field(..., ge=0.0, le=100.0)
    memory_used_mb: float = Field(..., ge=0.0)
    memory_available_mb: float = Field(..., ge=0.0)
    memory_total_mb: float = Field(..., gt=0.0)
    swap_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    # Disk
    disk_percent: float = Field(..., ge=0.0, le=100.0)
    disk_used_gb: float = Field(..., ge=0.0)
    disk_total_gb: float = Field(..., gt=0.0)
    disk_partitions: List[DiskPartitionSchema] = Field(default_factory=list, max_length=64)

    # Network (cumulative counters + throughput bps)
    net_bytes_sent: int = Field(default=0, ge=0)
    net_bytes_recv: int = Field(default=0, ge=0)
    net_packets_sent: int = Field(default=0, ge=0)
    net_packets_recv: int = Field(default=0, ge=0)
    net_interface: str = Field(default="all", max_length=64)
    net_upload_bps: float = Field(default=0.0, ge=0.0)
    net_download_bps: float = Field(default=0.0, ge=0.0)

    # System
    load_1m: float = Field(default=0.0, ge=0.0)
    load_5m: float = Field(default=0.0, ge=0.0)
    load_15m: float = Field(default=0.0, ge=0.0)
    uptime_seconds: int = Field(default=0, ge=0)
    process_count: int = Field(default=0, ge=0)
    top_processes: List[ProcessInfoSchema] = Field(default_factory=list, max_length=100)

    host_info: Optional[HostInfoSchema] = None
    is_demo: Optional[bool] = None


class MetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: str
    timestamp: datetime
    cpu_percent: float
    cpu_user: float
    cpu_system: float
    cpu_iowait: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    memory_total_mb: float
    swap_percent: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_partitions: List[dict]
    net_bytes_sent: int
    net_bytes_recv: int
    net_packets_sent: int
    net_packets_recv: int
    net_interface: str
    net_upload_bps: float
    net_download_bps: float
    load_1m: float
    load_5m: float
    load_15m: float
    uptime_seconds: int
    process_count: int
    top_processes: List[dict]
    is_demo: bool


class MetricIngestResponse(BaseModel):
    status: str = "accepted"
    metric_id: int
    server_id: str
    server_status: str
    health_score: float
    alerts_triggered: int
    alerts_resolved: int
    recommended_interval_seconds: int


class ProcessListResponse(BaseModel):
    server_id: str
    server_name: str
    is_demo: bool
    timestamp: Optional[datetime] = None
    total_processes: int
    processes: List[ProcessInfoSchema]

