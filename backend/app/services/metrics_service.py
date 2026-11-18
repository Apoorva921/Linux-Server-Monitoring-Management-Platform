from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models import Alert, Server, ServerMetric, SystemSettings
from app.schemas.metric import MetricIngestRequest
from app.services.alert_engine import evaluate_metric_alerts
from app.services.health_scoring import calculate_health_score


def ingest_server_metric(
    db: Session,
    server: Server,
    payload: MetricIngestRequest,
) -> Tuple[ServerMetric, List[Dict[str, Any]], int, int, int]:
    """
    Persist an incoming metric snapshot, update server metadata,
    evaluate alerts, recalculate health score, and prepare WebSocket broadcast events.
    """
    now = datetime.now(timezone.utc)
    metric_ts = payload.timestamp
    if metric_ts is None:
        metric_ts = now
    elif metric_ts.tzinfo is None:
        metric_ts = metric_ts.replace(tzinfo=timezone.utc)
    else:
        metric_ts = metric_ts.astimezone(timezone.utc)

    is_demo = server.is_demo if payload.is_demo is None else (server.is_demo or payload.is_demo)

    # Update host metadata if provided
    if payload.host_info:
        hi = payload.host_info
        if hi.hostname:
            server.hostname = hi.hostname
        if hi.ip_address:
            server.ip_address = hi.ip_address
        if hi.os_name:
            server.os_name = hi.os_name
        if hi.os_version:
            server.os_version = hi.os_version
        if hi.kernel_version:
            server.kernel_version = hi.kernel_version
        if hi.architecture:
            server.architecture = hi.architecture
        if hi.cpu_cores:
            server.cpu_cores = hi.cpu_cores
        if hi.agent_version:
            server.agent_version = hi.agent_version

    server.total_memory_mb = payload.memory_total_mb
    server.total_disk_gb = payload.disk_total_gb
    server.uptime_seconds = payload.uptime_seconds
    server.load_avg_1m = payload.load_1m
    server.load_avg_5m = payload.load_5m
    server.load_avg_15m = payload.load_15m
    server.last_heartbeat = now
    server.updated_at = now

    metric = ServerMetric(
        server_id=server.id,
        timestamp=metric_ts,
        cpu_percent=payload.cpu_percent,
        cpu_user=payload.cpu_user,
        cpu_system=payload.cpu_system,
        cpu_iowait=payload.cpu_iowait,
        memory_percent=payload.memory_percent,
        memory_used_mb=payload.memory_used_mb,
        memory_available_mb=payload.memory_available_mb,
        memory_total_mb=payload.memory_total_mb,
        swap_percent=payload.swap_percent,
        disk_percent=payload.disk_percent,
        disk_used_gb=payload.disk_used_gb,
        disk_total_gb=payload.disk_total_gb,
        disk_partitions=[p.model_dump() for p in payload.disk_partitions],
        net_bytes_sent=payload.net_bytes_sent,
        net_bytes_recv=payload.net_bytes_recv,
        net_packets_sent=payload.net_packets_sent,
        net_packets_recv=payload.net_packets_recv,
        net_interface=payload.net_interface,
        net_upload_bps=payload.net_upload_bps,
        net_download_bps=payload.net_download_bps,
        load_1m=payload.load_1m,
        load_5m=payload.load_5m,
        load_15m=payload.load_15m,
        uptime_seconds=payload.uptime_seconds,
        process_count=payload.process_count,
        top_processes=[p.model_dump() for p in payload.top_processes],
        is_demo=is_demo,
    )
    db.add(metric)
    db.flush()

    # Evaluate alert rules
    alert_events, triggered, resolved = evaluate_metric_alerts(db, server, metric)

    # Count active/acknowledged alerts for health score
    open_alerts = (
        db.query(Alert)
        .filter(Alert.server_id == server.id, Alert.status.in_(["active", "acknowledged"]))
        .all()
    )
    critical_count = sum(1 for a in open_alerts if a.severity == "critical")
    warning_count = sum(1 for a in open_alerts if a.severity == "warning")

    health = calculate_health_score(
        is_online=True,
        cpu_percent=metric.cpu_percent,
        memory_percent=metric.memory_percent,
        disk_percent=metric.disk_percent,
        active_critical_alerts=critical_count,
        active_warning_alerts=warning_count,
    )
    server.health_score = health["score"]
    server.status = health["status"]
    server.health_explanation = health

    sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    interval_seconds = sys_settings.monitoring_interval_seconds if sys_settings else 5

    db.commit()
    db.refresh(metric)

    ws_events: List[Dict[str, Any]] = [
        {
            "type": "metric_update",
            "server_id": server.id,
            "server_name": server.display_name,
            "is_demo": is_demo,
            "data": {
                "timestamp": metric.timestamp.isoformat(),
                "cpu_percent": metric.cpu_percent,
                "memory_percent": metric.memory_percent,
                "memory_used_mb": metric.memory_used_mb,
                "memory_total_mb": metric.memory_total_mb,
                "disk_percent": metric.disk_percent,
                "disk_used_gb": metric.disk_used_gb,
                "disk_total_gb": metric.disk_total_gb,
                "net_upload_bps": metric.net_upload_bps,
                "net_download_bps": metric.net_download_bps,
                "net_bytes_sent": metric.net_bytes_sent,
                "net_bytes_recv": metric.net_bytes_recv,
                "load_1m": metric.load_1m,
                "load_5m": metric.load_5m,
                "load_15m": metric.load_15m,
                "uptime_seconds": metric.uptime_seconds,
                "process_count": metric.process_count,
                "status": server.status,
                "health_score": server.health_score,
                "health_explanation": server.health_explanation,
            },
        }
    ]
    ws_events.extend(alert_events)
    return metric, ws_events, triggered, resolved, interval_seconds

