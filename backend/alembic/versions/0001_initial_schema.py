"""Initial SentinelOps schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
bigint_pk_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "servers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("os_name", sa.String(length=128), nullable=False),
        sa.Column("os_version", sa.String(length=128), nullable=False),
        sa.Column("kernel_version", sa.String(length=128), nullable=False),
        sa.Column("architecture", sa.String(length=64), nullable=False),
        sa.Column("cpu_cores", sa.Integer(), nullable=False),
        sa.Column("total_memory_mb", sa.Float(), nullable=False),
        sa.Column("total_disk_gb", sa.Float(), nullable=False),
        sa.Column("agent_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("health_explanation", json_type, nullable=True),
        sa.Column("uptime_seconds", sa.BigInteger(), nullable=False),
        sa.Column("load_avg_1m", sa.Float(), nullable=False),
        sa.Column("load_avg_5m", sa.Float(), nullable=False),
        sa.Column("load_avg_15m", sa.Float(), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("tags", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_servers_hostname", "servers", ["hostname"])
    op.create_index("ix_servers_status", "servers", ["status"])
    op.create_index("ix_servers_last_heartbeat", "servers", ["last_heartbeat"])
    op.create_index("ix_servers_is_demo", "servers", ["is_demo"])
    op.create_index("ix_servers_status_demo", "servers", ["status", "is_demo"])

    op.create_table(
        "agent_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("server_id", sa.String(length=36), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_prefix", sa.String(length=24), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_tokens_server_id", "agent_tokens", ["server_id"])
    op.create_index("ix_agent_tokens_token_hash", "agent_tokens", ["token_hash"], unique=True)
    op.create_index("ix_agent_tokens_is_active", "agent_tokens", ["is_active"])

    op.create_table(
        "server_metrics",
        sa.Column("id", bigint_pk_type, primary_key=True, autoincrement=True),
        sa.Column("server_id", sa.String(length=36), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=False),
        sa.Column("cpu_user", sa.Float(), nullable=False),
        sa.Column("cpu_system", sa.Float(), nullable=False),
        sa.Column("cpu_iowait", sa.Float(), nullable=False),
        sa.Column("memory_percent", sa.Float(), nullable=False),
        sa.Column("memory_used_mb", sa.Float(), nullable=False),
        sa.Column("memory_available_mb", sa.Float(), nullable=False),
        sa.Column("memory_total_mb", sa.Float(), nullable=False),
        sa.Column("swap_percent", sa.Float(), nullable=False),
        sa.Column("disk_percent", sa.Float(), nullable=False),
        sa.Column("disk_used_gb", sa.Float(), nullable=False),
        sa.Column("disk_total_gb", sa.Float(), nullable=False),
        sa.Column("disk_partitions", json_type, nullable=False),
        sa.Column("net_bytes_sent", sa.BigInteger(), nullable=False),
        sa.Column("net_bytes_recv", sa.BigInteger(), nullable=False),
        sa.Column("net_packets_sent", sa.BigInteger(), nullable=False),
        sa.Column("net_packets_recv", sa.BigInteger(), nullable=False),
        sa.Column("net_interface", sa.String(length=64), nullable=False),
        sa.Column("net_upload_bps", sa.Float(), nullable=False),
        sa.Column("net_download_bps", sa.Float(), nullable=False),
        sa.Column("load_1m", sa.Float(), nullable=False),
        sa.Column("load_5m", sa.Float(), nullable=False),
        sa.Column("load_15m", sa.Float(), nullable=False),
        sa.Column("uptime_seconds", sa.BigInteger(), nullable=False),
        sa.Column("process_count", sa.Integer(), nullable=False),
        sa.Column("top_processes", json_type, nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_server_metrics_server_id", "server_metrics", ["server_id"])
    op.create_index("ix_server_metrics_timestamp", "server_metrics", ["timestamp"])
    op.create_index("ix_server_metrics_server_ts", "server_metrics", ["server_id", "timestamp"])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("server_id", sa.String(length=36), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("metric_type", sa.String(length=32), nullable=False),
        sa.Column("warning_threshold", sa.Float(), nullable=False),
        sa.Column("critical_threshold", sa.Float(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_rules_server_id", "alert_rules", ["server_id"])
    op.create_index("ix_alert_rules_metric_type", "alert_rules", ["metric_type"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("server_id", sa.String(length=36), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metric_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("acknowledged_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_server_id", "alerts", ["server_id"])
    op.create_index("ix_alerts_metric_type", "alerts", ["metric_type"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_server_metric_status", "alerts", ["server_id", "metric_type", "status"])

    op.create_table(
        "system_logs",
        sa.Column("id", bigint_pk_type, primary_key=True, autoincrement=True),
        sa.Column("server_id", sa.String(length=36), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_logs_server_id", "system_logs", ["server_id"])
    op.create_index("ix_system_logs_timestamp", "system_logs", ["timestamp"])
    op.create_index("ix_system_logs_severity", "system_logs", ["severity"])
    op.create_index("ix_system_logs_source", "system_logs", ["source"])
    op.create_index("ix_system_logs_server_ts", "system_logs", ["server_id", "timestamp"])
    op.create_index("ix_system_logs_severity_ts", "system_logs", ["severity", "timestamp"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("monitoring_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("offline_threshold_seconds", sa.Integer(), nullable=False),
        sa.Column("metric_retention_days", sa.Integer(), nullable=False),
        sa.Column("log_sources", json_type, nullable=False),
        sa.Column("enable_journalctl", sa.Boolean(), nullable=False),
        sa.Column("max_processes_per_snapshot", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("system_logs")
    op.drop_table("alerts")
    op.drop_table("alert_rules")
    op.drop_table("server_metrics")
    op.drop_table("agent_tokens")
    op.drop_table("servers")
    op.drop_table("users")

