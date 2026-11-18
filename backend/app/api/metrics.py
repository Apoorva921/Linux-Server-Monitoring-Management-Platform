from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_agent_server, get_current_user
from app.database.session import get_db
from app.models import Server, ServerMetric, User
from app.schemas.metric import (
    MetricIngestRequest,
    MetricIngestResponse,
    MetricResponse,
    ProcessInfoSchema,
    ProcessListResponse,
)
from app.services.metrics_service import ingest_server_metric
from app.websocket.manager import ws_manager

router = APIRouter(tags=["Monitoring & Metrics"])

RANGE_DELTAS = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


@router.post(
    "/api/metrics/ingest",
    response_model=MetricIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_metrics(
    payload: MetricIngestRequest,
    server: Server = Depends(get_authenticated_agent_server),
    db: Session = Depends(get_db),
) -> MetricIngestResponse:
    if payload.server_id and payload.server_id != server.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "server_id_mismatch",
                "message": "Agent API token does not match the provided server_id.",
            },
        )

    metric, ws_events, triggered, resolved, interval = ingest_server_metric(db, server, payload)

    for event in ws_events:
        await ws_manager.broadcast(event, server_id=server.id)

    return MetricIngestResponse(
        status="accepted",
        metric_id=metric.id,
        server_id=server.id,
        server_status=server.status,
        health_score=server.health_score,
        alerts_triggered=triggered,
        alerts_resolved=resolved,
        recommended_interval_seconds=interval,
    )


@router.get("/api/servers/{server_id}/metrics", response_model=Optional[MetricResponse])
def get_latest_server_metrics(
    server_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Optional[MetricResponse]:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "server_not_found", "message": f"Server '{server_id}' not found."},
        )
    metric = (
        db.query(ServerMetric)
        .filter(ServerMetric.server_id == server_id)
        .order_by(ServerMetric.timestamp.desc())
        .first()
    )
    return MetricResponse.model_validate(metric) if metric else None


@router.get("/api/servers/{server_id}/metrics/history", response_model=List[MetricResponse])
def get_server_metrics_history(
    server_id: str,
    time_range: Literal["15m", "1h", "6h", "24h", "7d"] = Query(default="1h", alias="range"),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> List[MetricResponse]:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "server_not_found", "message": f"Server '{server_id}' not found."},
        )

    cutoff = datetime.now(timezone.utc) - RANGE_DELTAS[time_range]
    rows = (
        db.query(ServerMetric)
        .filter(ServerMetric.server_id == server_id, ServerMetric.timestamp >= cutoff)
        .order_by(ServerMetric.timestamp.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()  # chronological order for charts
    return [MetricResponse.model_validate(r) for r in rows]


@router.get("/api/servers/{server_id}/processes", response_model=ProcessListResponse)
def get_server_processes(
    server_id: str,
    search: Optional[str] = Query(default=None, max_length=128),
    sort_by: Literal["cpu_percent", "memory_percent", "pid", "name"] = Query(default="cpu_percent"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProcessListResponse:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "server_not_found", "message": f"Server '{server_id}' not found."},
        )

    latest = (
        db.query(ServerMetric)
        .filter(ServerMetric.server_id == server_id)
        .order_by(ServerMetric.timestamp.desc())
        .first()
    )
    if not latest:
        return ProcessListResponse(
            server_id=server.id,
            server_name=server.display_name,
            is_demo=server.is_demo,
            timestamp=None,
            total_processes=0,
            processes=[],
        )

    procs = [ProcessInfoSchema(**p) for p in (latest.top_processes or [])]
    if search:
        q = search.strip().lower()
        procs = [
            p
            for p in procs
            if q in p.name.lower() or q in p.username.lower() or q in str(p.pid)
        ]

    reverse = order == "desc"
    if sort_by == "name":
        procs.sort(key=lambda p: p.name.lower(), reverse=reverse)
    else:
        procs.sort(key=lambda p: getattr(p, sort_by), reverse=reverse)

    return ProcessListResponse(
        server_id=server.id,
        server_name=server.display_name,
        is_demo=server.is_demo,
        timestamp=latest.timestamp,
        total_processes=latest.process_count,
        processes=procs,
    )

