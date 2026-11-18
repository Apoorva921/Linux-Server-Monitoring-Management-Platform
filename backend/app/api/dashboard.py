from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.servers import build_server_response
from app.database.session import get_db
from app.models import Alert, Server, ServerMetric, SystemLog, User
from app.schemas.alert import AlertResponse
from app.schemas.dashboard import DashboardSummaryResponse, FleetTrendPoint
from app.schemas.log import LogResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    now = datetime.now(timezone.utc)
    servers = db.query(Server).order_by(Server.created_at.desc()).all()
    server_responses = [build_server_response(db, s) for s in servers]
    server_names = {s.id: s.display_name for s in servers}

    total_servers = len(servers)
    offline_servers = sum(1 for s in servers if s.status == "offline")
    online_servers = total_servers - offline_servers
    healthy_servers = sum(1 for s in servers if s.status == "healthy")
    warning_servers = sum(1 for s in servers if s.status == "warning")
    critical_servers = sum(1 for s in servers if s.status == "critical")

    # Fleet averages across online servers with metrics
    online_with_metrics = [
        sr.latest_metric
        for sr in server_responses
        if sr.status != "offline" and sr.latest_metric is not None
    ]
    if online_with_metrics:
        avg_cpu = round(sum(m.cpu_percent for m in online_with_metrics) / len(online_with_metrics), 2)
        avg_mem = round(sum(m.memory_percent for m in online_with_metrics) / len(online_with_metrics), 2)
        avg_disk = round(sum(m.disk_percent for m in online_with_metrics) / len(online_with_metrics), 2)
        total_upload = round(sum(m.net_upload_bps for m in online_with_metrics), 2)
        total_download = round(sum(m.net_download_bps for m in online_with_metrics), 2)
    else:
        avg_cpu = avg_mem = avg_disk = total_upload = total_download = 0.0

    open_alerts = db.query(Alert).filter(Alert.status.in_(["active", "acknowledged"])).all()
    active_alerts = len(open_alerts)
    critical_alerts = sum(1 for a in open_alerts if a.severity == "critical")
    warning_alerts = sum(1 for a in open_alerts if a.severity == "warning")

    recent_alert_rows = db.query(Alert).order_by(Alert.created_at.desc()).limit(10).all()
    recent_alerts = []
    for a in recent_alert_rows:
        item = AlertResponse.model_validate(a)
        item.server_name = server_names.get(a.server_id, a.server_id)
        recent_alerts.append(item)

    recent_log_rows = db.query(SystemLog).order_by(SystemLog.timestamp.desc(), SystemLog.id.desc()).limit(12).all()
    recent_logs = []
    for lg in recent_log_rows:
        item = LogResponse.model_validate(lg)
        item.server_name = server_names.get(lg.server_id, lg.server_id)
        recent_logs.append(item)

    # Fleet trend series over the last 30 minutes bucketed into 15-second intervals
    cutoff = now - timedelta(minutes=30)
    recent_metrics = (
        db.query(ServerMetric)
        .filter(ServerMetric.timestamp >= cutoff)
        .order_by(ServerMetric.timestamp.asc())
        .limit(1200)
        .all()
    )
    buckets: dict[datetime, list[ServerMetric]] = defaultdict(list)
    for m in recent_metrics:
        ts = m.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        bucket_sec = (ts.second // 15) * 15
        bucket_ts = ts.replace(second=bucket_sec, microsecond=0)
        buckets[bucket_ts].append(m)

    trend_series = []
    for bts in sorted(buckets.keys())[-60:]:
        pts = buckets[bts]
        n = len(pts)
        trend_series.append(
            FleetTrendPoint(
                timestamp=bts,
                avg_cpu_percent=round(sum(p.cpu_percent for p in pts) / n, 2),
                avg_memory_percent=round(sum(p.memory_percent for p in pts) / n, 2),
                avg_disk_percent=round(sum(p.disk_percent for p in pts) / n, 2),
                total_upload_bps=round(sum(p.net_upload_bps for p in pts), 2),
                total_download_bps=round(sum(p.net_download_bps for p in pts), 2),
            )
        )

    return DashboardSummaryResponse(
        total_servers=total_servers,
        online_servers=online_servers,
        offline_servers=offline_servers,
        healthy_servers=healthy_servers,
        warning_servers=warning_servers,
        critical_servers=critical_servers,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        avg_cpu_percent=avg_cpu,
        avg_memory_percent=avg_mem,
        avg_disk_percent=avg_disk,
        total_net_upload_bps=total_upload,
        total_net_download_bps=total_download,
        has_demo_data=any(s.is_demo for s in servers),
        has_real_data=any(not s.is_demo for s in servers),
        servers=server_responses,
        recent_alerts=recent_alerts,
        recent_logs=recent_logs,
        trend_series=trend_series,
        generated_at=now,
    )

