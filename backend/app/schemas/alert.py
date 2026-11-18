from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    server_id: str
    server_name: str = ""
    rule_id: Optional[str] = None
    metric_type: str
    title: str
    description: str
    severity: str
    metric_value: float
    threshold_value: float
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class AlertSummaryResponse(BaseModel):
    total: int
    active: int
    acknowledged: int
    resolved: int
    critical_active: int
    warning_active: int

