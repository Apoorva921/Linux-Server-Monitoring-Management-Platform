import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_agent_server, get_current_user
from app.database.session import get_db
from app.models import Server, SystemLog, User
from app.schemas.common import PaginatedResponse
from app.schemas.log import LogBatchIngestRequest, LogBatchIngestResponse, LogResponse
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/api/logs", tags=["System Logs"])


def _query_logs(
    db: Session,
    *,
    keyword: Optional[str] = None,
    server_id: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[LogResponse]:
    query = db.query(SystemLog)

    if server_id:
        query = query.filter(SystemLog.server_id == server_id)
    if severity:
        query = query.filter(SystemLog.severity == severity.upper())
    if source:
        query = query.filter(SystemLog.source.ilike(f"%{source.strip()}%"))
    if start_date:
        query = query.filter(SystemLog.timestamp >= start_date)
    if end_date:
        query = query.filter(SystemLog.timestamp <= end_date)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SystemLog.message.ilike(pattern),
                SystemLog.source.ilike(pattern),
                SystemLog.hostname.ilike(pattern),
                SystemLog.raw_line.ilike(pattern),
            )
        )

    total = query.count()
    rows = (
        query.order_by(SystemLog.timestamp.desc(), SystemLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    server_ids = {r.server_id for r in rows}
    server_names = {
        s.id: s.display_name
        for s in db.query(Server.id, Server.display_name).filter(Server.id.in_(server_ids)).all()
    } if server_ids else {}

    items = []
    for r in rows:
        item = LogResponse.model_validate(r)
        item.server_name = server_names.get(r.server_id, r.server_id)
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/ingest", response_model=LogBatchIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(
    payload: LogBatchIngestRequest,
    server: Server = Depends(get_authenticated_agent_server),
    db: Session = Depends(get_db),
) -> LogBatchIngestResponse:
    if payload.server_id and payload.server_id != server.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "server_id_mismatch", "message": "Agent token does not match server_id."},
        )

    now = datetime.now(timezone.utc)
    is_demo = server.is_demo if payload.is_demo is None else (server.is_demo or payload.is_demo)
    log_models = []
    for entry in payload.entries:
        ts = entry.timestamp or now
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        log_models.append(
            SystemLog(
                server_id=server.id,
                timestamp=ts,
                severity=entry.severity.upper(),
                source=entry.source,
                hostname=entry.hostname or server.hostname,
                message=entry.message,
                raw_line=entry.raw_line or entry.message,
                is_demo=is_demo,
                created_at=now,
            )
        )

    db.add_all(log_models)
    db.commit()

    # Notify WebSocket clients of high-severity log arrivals
    high_sev = [m for m in log_models if m.severity in ("ERROR", "CRITICAL", "WARNING")]
    if high_sev:
        latest_high = high_sev[-1]
        await ws_manager.broadcast(
            {
                "type": "log_event",
                "server_id": server.id,
                "server_name": server.display_name,
                "data": {
                    "id": latest_high.id,
                    "timestamp": latest_high.timestamp.isoformat(),
                    "severity": latest_high.severity,
                    "source": latest_high.source,
                    "message": latest_high.message,
                    "is_demo": is_demo,
                },
            },
            server_id=server.id,
        )

    return LogBatchIngestResponse(
        status="accepted",
        ingested_count=len(log_models),
        server_id=server.id,
    )


@router.get("", response_model=PaginatedResponse[LogResponse])
def list_logs(
    server_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse[LogResponse]:
    return _query_logs(
        db,
        server_id=server_id,
        severity=severity,
        source=source,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=PaginatedResponse[LogResponse])
def search_logs(
    q: Optional[str] = Query(default=None, max_length=256),
    server_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse[LogResponse]:
    return _query_logs(
        db,
        keyword=q,
        server_id=server_id,
        severity=severity,
        source=source,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

