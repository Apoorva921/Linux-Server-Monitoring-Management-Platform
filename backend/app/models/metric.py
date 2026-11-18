from typing import Any, Dict, List

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, BigIntPKType, JSONType, utcnow


class ServerMetric(Base):
    __tablename__ = "server_metrics"

    id: Mapped[int] = mapped_column(BigIntPKType, primary_key=True, autoincrement=True)
    server_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    # CPU
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_user: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cpu_system: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cpu_iowait: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Memory
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_used_mb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_available_mb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_total_mb: Mapped[float] = mapped_column(Float, nullable=False)
    swap_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Disk
    disk_percent: Mapped[float] = mapped_column(Float, nullable=False)
    disk_used_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_total_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_partitions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)

    # Network (cumulative counters vs real-time throughput clearly separated)
    net_bytes_sent: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_bytes_recv: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_packets_sent: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_packets_recv: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_interface: Mapped[str] = mapped_column(String(64), nullable=False, default="all")
    net_upload_bps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    net_download_bps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # System Load & Processes
    load_1m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    load_5m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    load_15m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    uptime_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    process_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_processes: Mapped[List[Dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)

    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    server = relationship("Server", back_populates="metrics")

    __table_args__ = (
        Index("ix_server_metrics_server_ts", "server_id", "timestamp"),
    )

