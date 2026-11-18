from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Portable types that use optimal native PostgreSQL types in production
# while remaining compatible with SQLite for isolated unit testing.
JSONType = JSON().with_variant(JSONB(), "postgresql")
BigIntPKType = BigInteger().with_variant(Integer(), "sqlite")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def UtcDateTime(nullable: bool = False) -> DateTime:
    return DateTime(timezone=True)

