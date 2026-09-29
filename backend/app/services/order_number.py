"""Order number generation: ORD-YYYYMMDD-NNNN, unique per database."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.order import OrderRepository
from app.utils.time import utc_today


def next_order_number(db: Session) -> str:
    prefix = f"ORD-{utc_today():%Y%m%d}-"
    latest = OrderRepository(db).latest_for_prefix(prefix)
    sequence = int(latest.rsplit("-", 1)[1]) + 1 if latest else 1
    return f"{prefix}{sequence:04d}"
