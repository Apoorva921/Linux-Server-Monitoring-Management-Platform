from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, hash_agent_token, verify_agent_token
from app.database.session import get_db
from app.models import AgentToken, Server, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Missing or invalid authorization token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == payload["sub"], User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "user_not_found", "message": "User account is inactive or does not exist."},
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Administrator privileges are required for this action."},
        )
    return current_user


def get_authenticated_agent_server(
    x_agent_token: Optional[str] = Header(default=None, alias="X-Agent-Token"),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Server:
    """Authenticate a monitoring agent via X-Agent-Token (or Bearer sops_...) header."""
    raw_token = x_agent_token
    if not raw_token and authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ", 1)[1].strip()

    if not raw_token or not raw_token.startswith("sops_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_agent_token", "message": "Valid monitoring agent API token required."},
        )

    token_hash = hash_agent_token(raw_token)
    token_record = (
        db.query(AgentToken)
        .filter(AgentToken.token_hash == token_hash, AgentToken.is_active.is_(True))
        .first()
    )
    if not token_record or not verify_agent_token(raw_token, token_record.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_agent_token", "message": "Agent API token is invalid or revoked."},
        )

    server = db.query(Server).filter(Server.id == token_record.server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "server_not_found", "message": "Registered server for this token no longer exists."},
        )

    token_record.last_used_at = datetime.now(timezone.utc)
    db.flush()
    return server

