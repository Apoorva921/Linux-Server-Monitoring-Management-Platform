from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.database.init_db import seed_initial_data
from app.database.session import get_db
from app.models import AlertRule, SystemSettings, User
from app.schemas.settings import AlertThresholdConfig, SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _build_settings_response(db: Session) -> SettingsResponse:
    sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not sys_settings:
        seed_initial_data(db)
        sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()

    global_rules = (
        db.query(AlertRule)
        .filter(AlertRule.server_id.is_(None))
        .order_by(AlertRule.metric_type.asc())
        .all()
    )
    thresholds = [
        AlertThresholdConfig(
            metric_type=r.metric_type,
            name=r.name,
            warning_threshold=r.warning_threshold,
            critical_threshold=r.critical_threshold,
            cooldown_seconds=r.cooldown_seconds,
            is_enabled=r.is_enabled,
        )
        for r in global_rules
    ]
    return SettingsResponse(
        monitoring_interval_seconds=sys_settings.monitoring_interval_seconds,
        offline_threshold_seconds=sys_settings.offline_threshold_seconds,
        metric_retention_days=sys_settings.metric_retention_days,
        log_sources=sys_settings.log_sources,
        enable_journalctl=sys_settings.enable_journalctl,
        max_processes_per_snapshot=sys_settings.max_processes_per_snapshot,
        thresholds=thresholds,
        updated_at=sys_settings.updated_at,
    )


@router.get("", response_model=SettingsResponse)
def get_system_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SettingsResponse:
    return _build_settings_response(db)


@router.put("", response_model=SettingsResponse)
def update_system_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SettingsResponse:
    sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not sys_settings:
        seed_initial_data(db)
        sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()

    now = datetime.now(timezone.utc)
    sys_settings.monitoring_interval_seconds = payload.monitoring_interval_seconds
    sys_settings.offline_threshold_seconds = payload.offline_threshold_seconds
    sys_settings.metric_retention_days = payload.metric_retention_days
    sys_settings.log_sources = payload.log_sources
    sys_settings.enable_journalctl = payload.enable_journalctl
    sys_settings.max_processes_per_snapshot = payload.max_processes_per_snapshot
    sys_settings.updated_at = now

    for cfg in payload.thresholds:
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.server_id.is_(None), AlertRule.metric_type == cfg.metric_type)
            .first()
        )
        if rule:
            rule.name = cfg.name
            rule.warning_threshold = cfg.warning_threshold
            rule.critical_threshold = cfg.critical_threshold
            rule.cooldown_seconds = cfg.cooldown_seconds
            rule.is_enabled = cfg.is_enabled
            rule.updated_at = now
        else:
            db.add(
                AlertRule(
                    server_id=None,
                    name=cfg.name,
                    metric_type=cfg.metric_type,
                    warning_threshold=cfg.warning_threshold,
                    critical_threshold=cfg.critical_threshold,
                    cooldown_seconds=cfg.cooldown_seconds,
                    is_enabled=cfg.is_enabled,
                )
            )

    db.commit()
    return _build_settings_response(db)

