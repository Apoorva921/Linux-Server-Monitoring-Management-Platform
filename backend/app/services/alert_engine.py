from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models import Alert, AlertRule, Server, ServerMetric

METRIC_LABELS = {
    "cpu": ("CPU Utilization", "%"),
    "memory": ("Memory Utilization", "%"),
    "disk": ("Disk Utilization", "%"),
    "network_upload": ("Network Upload Throughput", "MB/s"),
    "network_download": ("Network Download Throughput", "MB/s"),
}


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_effective_rules(db: Session, server_id: str) -> Dict[str, AlertRule]:
    """Return effective enabled alert rules for a server (per-server rules override global rules)."""
    global_rules = (
        db.query(AlertRule)
        .filter(AlertRule.server_id.is_(None), AlertRule.is_enabled.is_(True))
        .all()
    )
    server_rules = (
        db.query(AlertRule)
        .filter(AlertRule.server_id == server_id, AlertRule.is_enabled.is_(True))
        .all()
    )
    effective: Dict[str, AlertRule] = {r.metric_type: r for r in global_rules}
    for r in server_rules:
        effective[r.metric_type] = r
    return effective


def _extract_metric_values(metric: ServerMetric) -> Dict[str, float]:
    return {
        "cpu": round(metric.cpu_percent, 2),
        "memory": round(metric.memory_percent, 2),
        "disk": round(metric.disk_percent, 2),
        "network_upload": round(metric.net_upload_bps / (1024 * 1024), 2),  # MB/s
        "network_download": round(metric.net_download_bps / (1024 * 1024), 2),  # MB/s
    }


def evaluate_metric_alerts(
    db: Session,
    server: Server,
    metric: ServerMetric,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Evaluate incoming server metrics against alert rules.

    Features:
      - Prevents duplicate alerts on consecutive intervals.
      - Escalates an active warning alert to critical if critical threshold is crossed.
      - Applies configurable cooldown window after recent resolution to avoid flapping.
      - Automatically resolves active/acknowledged alerts when metrics recover below warning threshold.

    Returns:
      (ws_events, alerts_triggered_count, alerts_resolved_count)
    """
    now = datetime.now(timezone.utc)
    rules = _get_effective_rules(db, server.id)
    values = _extract_metric_values(metric)
    ws_events: List[Dict[str, Any]] = []
    triggered = 0
    resolved = 0

    for metric_type, value in values.items():
        rule = rules.get(metric_type)
        if not rule:
            continue

        label, unit = METRIC_LABELS.get(metric_type, (metric_type.upper(), ""))

        # Determine breached severity
        breached_severity = None
        threshold_hit = 0.0
        if value >= rule.critical_threshold:
            breached_severity = "critical"
            threshold_hit = rule.critical_threshold
        elif value >= rule.warning_threshold:
            breached_severity = "warning"
            threshold_hit = rule.warning_threshold

        open_alert = (
            db.query(Alert)
            .filter(
                Alert.server_id == server.id,
                Alert.metric_type == metric_type,
                Alert.status.in_(["active", "acknowledged"]),
            )
            .order_by(Alert.created_at.desc())
            .first()
        )

        if breached_severity is not None:
            if open_alert:
                # Duplicate prevention: update existing open alert; escalate if warning -> critical
                escalated = open_alert.severity == "warning" and breached_severity == "critical"
                open_alert.metric_value = value
                open_alert.updated_at = now
                if escalated:
                    open_alert.severity = "critical"
                    open_alert.threshold_value = threshold_hit
                    open_alert.title = f"CRITICAL: High {label} on {server.display_name}"
                    open_alert.description = (
                        f"{label} escalated to {value}{unit} on {server.hostname}, "
                        f"exceeding critical threshold of {threshold_hit}{unit}."
                    )
                    open_alert.status = "active"
                    db.flush()
                    ws_events.append(
                        {
                            "type": "alert_event",
                            "action": "escalated",
                            "server_id": server.id,
                            "data": _serialize_alert_event(open_alert, server.display_name),
                        }
                    )
                continue

            # Cooldown check: do not re-trigger if a recently resolved alert is still within cooldown
            last_resolved = (
                db.query(Alert)
                .filter(
                    Alert.server_id == server.id,
                    Alert.metric_type == metric_type,
                    Alert.status == "resolved",
                    Alert.resolved_at.is_not(None),
                )
                .order_by(Alert.resolved_at.desc())
                .first()
            )
            if last_resolved and last_resolved.resolved_at is not None:
                resolved_at_utc = _ensure_utc(last_resolved.resolved_at)
                if resolved_at_utc and (now - resolved_at_utc) < timedelta(seconds=rule.cooldown_seconds):
                    continue

            # Create new alert
            severity_prefix = "CRITICAL" if breached_severity == "critical" else "WARNING"
            alert = Alert(
                server_id=server.id,
                rule_id=rule.id,
                metric_type=metric_type,
                title=f"{severity_prefix}: High {label} on {server.display_name}",
                description=(
                    f"{label} reached {value}{unit} on {server.hostname} "
                    f"(threshold: {threshold_hit}{unit})."
                ),
                severity=breached_severity,
                metric_value=value,
                threshold_value=threshold_hit,
                status="active",
                is_demo=server.is_demo,
                created_at=now,
                updated_at=now,
            )
            db.add(alert)
            db.flush()
            triggered += 1
            ws_events.append(
                {
                    "type": "alert_event",
                    "action": "created",
                    "server_id": server.id,
                    "data": _serialize_alert_event(alert, server.display_name),
                }
            )
        else:
            # Recovery detection: metric returned strictly below warning threshold
            if open_alert:
                open_alert.status = "resolved"
                open_alert.resolved_at = now
                open_alert.updated_at = now
                open_alert.metric_value = value
                db.flush()
                resolved += 1
                ws_events.append(
                    {
                        "type": "alert_event",
                        "action": "resolved",
                        "server_id": server.id,
                        "data": _serialize_alert_event(open_alert, server.display_name),
                    }
                )

    # Also auto-resolve any active offline alert because server just reported metrics
    offline_alerts = (
        db.query(Alert)
        .filter(
            Alert.server_id == server.id,
            Alert.metric_type == "offline",
            Alert.status.in_(["active", "acknowledged"]),
        )
        .all()
    )
    for oa in offline_alerts:
        oa.status = "resolved"
        oa.resolved_at = now
        oa.updated_at = now
        resolved += 1
        ws_events.append(
            {
                "type": "alert_event",
                "action": "resolved",
                "server_id": server.id,
                "data": _serialize_alert_event(oa, server.display_name),
            }
        )

    return ws_events, triggered, resolved


def _serialize_alert_event(alert: Alert, server_name: str) -> Dict[str, Any]:
    return {
        "id": alert.id,
        "server_id": alert.server_id,
        "server_name": server_name,
        "metric_type": alert.metric_type,
        "title": alert.title,
        "description": alert.description,
        "severity": alert.severity,
        "metric_value": alert.metric_value,
        "threshold_value": alert.threshold_value,
        "status": alert.status,
        "is_demo": alert.is_demo,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }

