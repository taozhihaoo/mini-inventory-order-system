"""Naive-UTC clock helper and shared timestamp mixin."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC datetime, so SQLite storage and comparisons stay consistent."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_today() -> date:
    return utcnow().date()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
