from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.schemas.alert import AlertResponse
from app.schemas.log import LogResponse
from app.schemas.server import ServerResponse


class FleetTrendPoint(BaseModel):
    timestamp: datetime
    avg_cpu_percent: float
    avg_memory_percent: float
    avg_disk_percent: float
    total_upload_bps: float
    total_download_bps: float


class DashboardSummaryResponse(BaseModel):
    total_servers: int
    online_servers: int
    offline_servers: int
    healthy_servers: int
    warning_servers: int
    critical_servers: int
    active_alerts: int
    critical_alerts: int
    warning_alerts: int
    avg_cpu_percent: float
    avg_memory_percent: float
    avg_disk_percent: float
    total_net_upload_bps: float
    total_net_download_bps: float
    has_demo_data: bool
    has_real_data: bool
    servers: List[ServerResponse]
    recent_alerts: List[AlertResponse]
    recent_logs: List[LogResponse]
    trend_series: List[FleetTrendPoint]
    generated_at: datetime

