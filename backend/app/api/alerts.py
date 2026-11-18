import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models import Alert, Server, User
from app.schemas.alert import AlertResponse, AlertSummaryResponse
from app.schemas.common import PaginatedResponse
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


def _to_alert_response(alert: Alert, server_names: dict[str, str]) -> AlertResponse:
    item = AlertResponse.model_validate(alert)
    item.server_name = server_names.get(alert.server_id, alert.server_id)
    return item


@router.get("/summary", response_model=AlertSummaryResponse)
def get_alert_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertSummaryResponse:
    alerts = db.query(Alert).all()
    return AlertSummaryResponse(
        total=len(alerts),
        active=sum(1 for a in alerts if a.status == "active"),
        acknowledged=sum(1 for a in alerts if a.status == "acknowledged"),
        resolved=sum(1 for a in alerts if a.status == "resolved"),
        critical_active=sum(1 for a in alerts if a.status in ("active", "acknowledged") and a.severity == "critical"),
        warning_active=sum(1 for a in alerts if a.status in ("active", "acknowledged") and a.severity == "warning"),
    )


@router.get("", response_model=PaginatedResponse[AlertResponse])
def list_alerts(
    severity: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    server_id: Optional[str] = Query(default=None),
    metric_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse[AlertResponse]:
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity.lower())
    if status_filter:
        query = query.filter(Alert.status == status_filter.lower())
    if server_id:
        query = query.filter(Alert.server_id == server_id)
    if metric_type:
        query = query.filter(Alert.metric_type == metric_type.lower())

    total = query.count()
    alerts = (
        query.order_by(Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    server_ids = {a.server_id for a in alerts}
    server_names = {
        s.id: s.display_name
        for s in db.query(Server.id, Server.display_name).filter(Server.id.in_(server_ids)).all()
    } if server_ids else {}

    return PaginatedResponse(
        items=[_to_alert_response(a, server_names) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertResponse:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "alert_not_found", "message": f"Alert '{alert_id}' not found."},
        )
    server = db.query(Server.id, Server.display_name).filter(Server.id == alert.server_id).first()
    server_names = {server.id: server.display_name} if server else {}
    return _to_alert_response(alert, server_names)


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "alert_not_found", "message": f"Alert '{alert_id}' not found."},
        )
    if alert.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_transition", "message": "Cannot acknowledge a resolved alert."},
        )

    now = datetime.now(timezone.utc)
    alert.status = "acknowledged"
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = now
    alert.updated_at = now
    db.commit()
    db.refresh(alert)

    server = db.query(Server.id, Server.display_name).filter(Server.id == alert.server_id).first()
    server_names = {server.id: server.display_name} if server else {}
    resp = _to_alert_response(alert, server_names)

    await ws_manager.broadcast(
        {
            "type": "alert_event",
            "action": "acknowledged",
            "server_id": alert.server_id,
            "data": resp.model_dump(mode="json"),
        },
        server_id=alert.server_id,
    )
    return resp


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertResponse:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "alert_not_found", "message": f"Alert '{alert_id}' not found."},
        )

    now = datetime.now(timezone.utc)
    alert.status = "resolved"
    alert.resolved_at = now
    alert.updated_at = now
    db.commit()
    db.refresh(alert)

    server = db.query(Server.id, Server.display_name).filter(Server.id == alert.server_id).first()
    server_names = {server.id: server.display_name} if server else {}
    resp = _to_alert_response(alert, server_names)

    await ws_manager.broadcast(
        {
            "type": "alert_event",
            "action": "resolved",
            "server_id": alert.server_id,
            "data": resp.model_dump(mode="json"),
        },
        server_id=alert.server_id,
    )
    return resp

