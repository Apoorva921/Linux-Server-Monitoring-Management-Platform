import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.security import generate_agent_token
from app.database.session import get_db
from app.models import AgentToken, Alert, Server, ServerMetric, User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.server import (
    ServerMetricBrief,
    ServerRegisterRequest,
    ServerRegisterResponse,
    ServerResponse,
    TokenRotateResponse,
)

router = APIRouter(prefix="/api/servers", tags=["Servers"])


def build_server_response(db: Session, server: Server) -> ServerResponse:
    latest_metric = (
        db.query(ServerMetric)
        .filter(ServerMetric.server_id == server.id)
        .order_by(ServerMetric.timestamp.desc())
        .first()
    )
    active_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.server_id == server.id, Alert.status.in_(["active", "acknowledged"]))
        .scalar()
        or 0
    )
    data = ServerResponse.model_validate(server)
    data.latest_metric = ServerMetricBrief.model_validate(latest_metric) if latest_metric else None
    data.active_alert_count = int(active_alerts)
    return data


@router.get("", response_model=PaginatedResponse[ServerResponse])
def list_servers(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, max_length=128),
    is_demo: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PaginatedResponse[ServerResponse]:
    query = db.query(Server)
    if status_filter:
        query = query.filter(Server.status == status_filter.lower())
    if is_demo is not None:
        query = query.filter(Server.is_demo == is_demo)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Server.hostname.ilike(pattern),
                Server.display_name.ilike(pattern),
                Server.ip_address.ilike(pattern),
                Server.os_name.ilike(pattern),
            )
        )

    total = query.count()
    servers = (
        query.order_by(Server.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [build_server_response(db, srv) for srv in servers]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/register", response_model=ServerRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_server(
    payload: ServerRegisterRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ServerRegisterResponse:
    display_name = (payload.display_name or payload.hostname).strip()
    server = Server(
        hostname=payload.hostname.strip(),
        display_name=display_name,
        ip_address=payload.ip_address.strip(),
        os_name=payload.os_name.strip(),
        os_version=payload.os_version.strip(),
        kernel_version=payload.kernel_version.strip(),
        architecture=payload.architecture.strip(),
        cpu_cores=payload.cpu_cores,
        total_memory_mb=payload.total_memory_mb,
        total_disk_gb=payload.total_disk_gb,
        agent_version=payload.agent_version.strip(),
        status="offline",
        health_score=0.0,
        health_explanation={
            "score": 0.0,
            "status": "offline",
            "summary": "Awaiting first heartbeat from monitoring agent.",
            "deductions": [],
        },
        is_demo=payload.is_demo,
        tags=payload.tags,
    )
    db.add(server)
    db.flush()

    raw_token, token_prefix, token_hash = generate_agent_token()
    agent_token = AgentToken(
        server_id=server.id,
        token_prefix=token_prefix,
        token_hash=token_hash,
        name=f"{server.hostname}-agent-token",
        is_active=True,
    )
    db.add(agent_token)
    db.commit()
    db.refresh(server)

    return ServerRegisterResponse(
        server=build_server_response(db, server),
        api_token=raw_token,
        token_prefix=token_prefix,
    )


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(
    server_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ServerResponse:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "server_not_found", "message": f"Server '{server_id}' not found."},
        )
    return build_server_response(db, server)


@router.post("/{server_id}/rotate-token", response_model=TokenRotateResponse)
def rotate_server_token(
    server_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TokenRotateResponse:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "server_not_found", "message": f"Server '{server_id}' not found."},
        )

    now = datetime.now(timezone.utc)
    db.query(AgentToken).filter(
        AgentToken.server_id == server.id, AgentToken.is_active.is_(True)
    ).update({"is_active": False, "revoked_at": now})

    raw_token, token_prefix, token_hash = generate_agent_token()
    db.add(
        AgentToken(
            server_id=server.id,
            token_prefix=token_prefix,
            token_hash=token_hash,
            name=f"{server.hostname}-rotated-token",
            is_active=True,
        )
    )
    db.commit()

    return TokenRotateResponse(
        server_id=server.id,
        api_token=raw_token,
        token_prefix=token_prefix,
    )


@router.delete("/{server_id}", response_model=MessageResponse)
def delete_server(
    server_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> MessageResponse:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "server_not_found", "message": f"Server '{server_id}' not found."},
        )
    db.delete(server)
    db.commit()
    return MessageResponse(message=f"Server '{server.display_name}' deleted successfully.")

