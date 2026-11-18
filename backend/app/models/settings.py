from typing import List

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, JSONType, utcnow


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    monitoring_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    offline_threshold_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    metric_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    log_sources: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=lambda: ["/var/log/syslog", "/var/log/auth.log"],
    )
    enable_journalctl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_processes_per_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

