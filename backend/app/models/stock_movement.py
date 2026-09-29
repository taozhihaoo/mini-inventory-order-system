from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.time import utcnow


class MovementType:
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"

    ALL = (IN, OUT, ADJUSTMENT)


class StockMovement(Base):
    """Immutable audit trail of every stock change.

    quantity semantics: positive for IN / OUT (the moved amount), signed delta
    for ADJUSTMENT. stock_after records the product stock after this movement.
    """

    __tablename__ = "stock_movements"
    __table_args__ = (
        Index("ix_stock_movements_created_at", "created_at"),
        Index("ix_stock_movements_product_created", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(20))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    product = relationship("Product", back_populates="movements")
