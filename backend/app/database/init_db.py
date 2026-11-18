import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.base import Base
from app.models import AlertRule, SystemSettings, User

logger = logging.getLogger(__name__)

DEFAULT_ALERT_RULES = [
    {
        "name": "Global CPU Utilization",
        "metric_type": "cpu",
        "warning_threshold": 75.0,
        "critical_threshold": 90.0,
        "cooldown_seconds": 300,
    },
    {
        "name": "Global Memory Utilization",
        "metric_type": "memory",
        "warning_threshold": 80.0,
        "critical_threshold": 90.0,
        "cooldown_seconds": 300,
    },
    {
        "name": "Global Disk Utilization",
        "metric_type": "disk",
        "warning_threshold": 80.0,
        "critical_threshold": 90.0,
        "cooldown_seconds": 600,
    },
    {
        "name": "Global Network Upload Throughput (MB/s)",
        "metric_type": "network_upload",
        "warning_threshold": 50.0,
        "critical_threshold": 100.0,
        "cooldown_seconds": 300,
    },
    {
        "name": "Global Network Download Throughput (MB/s)",
        "metric_type": "network_download",
        "warning_threshold": 50.0,
        "critical_threshold": 100.0,
        "cooldown_seconds": 300,
    },
]


def seed_initial_data(db: Session) -> None:
    """Seed initial admin user, global alert rules, and system settings idempotently."""
    settings = get_settings()

    # 1. Seed system settings singleton
    sys_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not sys_settings:
        sys_settings = SystemSettings(
            id=1,
            monitoring_interval_seconds=settings.DEFAULT_MONITORING_INTERVAL_SECONDS,
            offline_threshold_seconds=settings.SERVER_OFFLINE_THRESHOLD_SECONDS,
            metric_retention_days=settings.DEFAULT_METRIC_RETENTION_DAYS,
            log_sources=["/var/log/syslog", "/var/log/auth.log"],
            enable_journalctl=True,
            max_processes_per_snapshot=30,
        )
        db.add(sys_settings)

    # 2. Seed global alert rules
    existing_global_types = {
        row[0]
        for row in db.query(AlertRule.metric_type).filter(AlertRule.server_id.is_(None)).all()
    }
    for rule_def in DEFAULT_ALERT_RULES:
        if rule_def["metric_type"] not in existing_global_types:
            db.add(AlertRule(server_id=None, **rule_def))

    # 3. Bootstrap initial admin user if no users exist
    user_count = db.query(User).count()
    if user_count == 0:
        admin_user = User(
            username=settings.INITIAL_ADMIN_USERNAME,
            email=settings.INITIAL_ADMIN_EMAIL,
            hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            full_name="System Administrator",
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        logger.info("Bootstrapped initial administrator user '%s'", settings.INITIAL_ADMIN_USERNAME)

    db.commit()


def create_tables_and_seed(bind_engine, db_session_factory) -> None:
    """Ensure schema exists and seed defaults."""
    Base.metadata.create_all(bind=bind_engine)
    db = db_session_factory()
    try:
        seed_initial_data(db)
    finally:
        db.close()

