import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, JSONType, utcnow


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="0.0.0.0")
    os_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Linux")
    os_version: Mapped[str] = mapped_column(String(128), nullable=False, default="Unknown")
    kernel_version: Mapped[str] = mapped_column(String(128), nullable=False, default="Unknown")
    architecture: Mapped[str] = mapped_column(String(64), nullable=False, default="x86_64")
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_memory_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_disk_gb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    agent_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="offline", index=True
    )  # healthy | warning | critical | offline
    health_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    health_explanation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    uptime_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    load_avg_1m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    load_avg_5m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    load_avg_15m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_heartbeat: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    tags: Mapped[List[str]] = mapped_column(JSONType, nullable=False, default=list)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    tokens = relationship("AgentToken", back_populates="server", cascade="all, delete-orphan")
    metrics = relationship("ServerMetric", back_populates="server", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="server", cascade="all, delete-orphan")
    logs = relationship("SystemLog", back_populates="server", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="server", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_servers_status_demo", "status", "is_demo"),
    )

