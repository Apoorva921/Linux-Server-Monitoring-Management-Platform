import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt

from app.core.config import get_settings

AGENT_TOKEN_PREFIX = "sops_"


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token. Returns None if invalid or expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access" or not payload.get("sub"):
            return None
        return payload
    except jwt.PyJWTError:
        return None


def generate_agent_token() -> Tuple[str, str, str]:
    """
    Generate a cryptographically secure monitoring agent API token.

    Returns:
        (raw_token, token_prefix, token_hash)
    """
    raw_token = f"{AGENT_TOKEN_PREFIX}{secrets.token_urlsafe(36)}"
    token_prefix = raw_token[:14]
    token_hash = hash_agent_token(raw_token)
    return raw_token, token_prefix, token_hash


def hash_agent_token(raw_token: str) -> str:
    """Compute an HMAC-SHA256 digest of an agent API token."""
    settings = get_settings()
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_agent_token(raw_token: str, expected_hash: str) -> bool:
    """Constant-time verification of an agent API token against its stored hash."""
    computed = hash_agent_token(raw_token)
    return hmac.compare_digest(computed, expected_hash)

