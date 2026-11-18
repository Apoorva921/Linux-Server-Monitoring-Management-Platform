import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.database.session import SessionLocal
from app.models import Alert, Server, ServerMetric, SystemLog, SystemSettings
from app.services.health_scoring import calculate_health_score
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def check_offline_servers_once() -> int:
    """Detect servers whose heartbeat expired and mark them offline."""
    db = SessionLocal()
    events = []
    marked_offline = 0
    try:
        sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
        threshold_sec = sys_settings.offline_threshold_seconds if sys_settings else 30
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=threshold_sec)

        online_servers = (
            db.query(Server)
            .filter(Server.status != "offline", Server.last_heartbeat.is_not(None))
            .all()
        )
        for srv in online_servers:
            hb = _ensure_utc(srv.last_heartbeat)
            if hb and hb < cutoff:
                srv.status = "offline"
                health = calculate_health_score(
                    is_online=False, cpu_percent=0, memory_percent=0, disk_percent=0
                )
                srv.health_score = health["score"]
                srv.health_explanation = health
                srv.updated_at = now
                marked_offline += 1

                existing_offline = (
                    db.query(Alert)
                    .filter(
                        Alert.server_id == srv.id,
                        Alert.metric_type == "offline",
                        Alert.status.in_(["active", "acknowledged"]),
                    )
                    .first()
                )
                if not existing_offline:
                    alert = Alert(
                        server_id=srv.id,
                        metric_type="offline",
                        title=f"CRITICAL: Server {srv.display_name} is Offline",
                        description=(
                            f"No heartbeat received from {srv.hostname} for over {threshold_sec} seconds."
                        ),
                        severity="critical",
                        metric_value=float(threshold_sec),
                        threshold_value=float(threshold_sec),
                        status="active",
                        is_demo=srv.is_demo,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(alert)

                events.append(
                    {
                        "type": "server_status",
                        "server_id": srv.id,
                        "status": "offline",
                        "health_score": 0.0,
                        "timestamp": now.isoformat(),
                    }
                )
        if marked_offline:
            db.commit()
    except Exception:
        logger.exception("Error while checking offline servers")
        db.rollback()
    finally:
        db.close()

    for ev in events:
        await ws_manager.broadcast(ev, server_id=ev["server_id"])
    return marked_offline


def prune_expired_data_once() -> tuple[int, int]:
    """Delete historical metrics and logs older than the configured retention period."""
    db = SessionLocal()
    try:
        sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
        retention_days = sys_settings.metric_retention_days if sys_settings else 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        deleted_metrics = (
            db.query(ServerMetric).filter(ServerMetric.timestamp < cutoff).delete(synchronize_session=False)
        )
        deleted_logs = (
            db.query(SystemLog).filter(SystemLog.timestamp < cutoff).delete(synchronize_session=False)
        )
        if deleted_metrics or deleted_logs:
            db.commit()
            logger.info(
                "Retention pruner removed %d metrics and %d logs older than %d days",
                deleted_metrics,
                deleted_logs,
                retention_days,
            )
        return deleted_metrics, deleted_logs
    except Exception:
        logger.exception("Error during retention pruning")
        db.rollback()
        return 0, 0
    finally:
        db.close()


async def background_monitor_loop(stop_event: asyncio.Event) -> None:
    """Periodic loop for offline server detection (every 10s) and retention pruning (every hour)."""
    ticks = 0
    while not stop_event.is_set():
        await check_offline_servers_once()
        if ticks % 360 == 0:  # Every ~60 minutes
            await asyncio.to_thread(prune_expired_data_once)
        ticks += 1
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            continue

