from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlertThresholdConfig(BaseModel):
    metric_type: str
    name: str
    warning_threshold: float = Field(..., ge=0.0)
    critical_threshold: float = Field(..., ge=0.0)
    cooldown_seconds: int = Field(default=300, ge=10, le=86400)
    is_enabled: bool = True

    @model_validator(mode="after")
    def check_thresholds(self) -> "AlertThresholdConfig":
        if self.critical_threshold < self.warning_threshold:
            raise ValueError(
                f"critical_threshold ({self.critical_threshold}) must be >= warning_threshold ({self.warning_threshold})"
            )
        return self


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    monitoring_interval_seconds: int
    offline_threshold_seconds: int
    metric_retention_days: int
    log_sources: List[str]
    enable_journalctl: bool
    max_processes_per_snapshot: int
    thresholds: List[AlertThresholdConfig]
    updated_at: datetime


class SettingsUpdateRequest(BaseModel):
    monitoring_interval_seconds: int = Field(..., ge=2, le=300)
    offline_threshold_seconds: int = Field(..., ge=10, le=3600)
    metric_retention_days: int = Field(..., ge=1, le=365)
    log_sources: List[str] = Field(default_factory=lambda: ["/var/log/syslog", "/var/log/auth.log"], max_length=20)
    enable_journalctl: bool = True
    max_processes_per_snapshot: int = Field(default=30, ge=5, le=100)
    thresholds: List[AlertThresholdConfig] = Field(default_factory=list)

