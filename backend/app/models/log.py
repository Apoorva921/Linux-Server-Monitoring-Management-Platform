from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, BigIntPKType, utcnow


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(BigIntPKType, primary_key=True, autoincrement=True)
    server_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="INFO", index=True
    )  # DEBUG | INFO | WARNING | ERROR | CRITICAL
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="syslog", index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_line: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    server = relationship("Server", back_populates="logs")

    __table_args__ = (
        Index("ix_system_logs_server_ts", "server_id", "timestamp"),
        Index("ix_system_logs_severity_ts", "severity", "timestamp"),
    )

