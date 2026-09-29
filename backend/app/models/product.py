from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.time import TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        CheckConstraint("cost_price IS NULL OR cost_price >= 0", name="ck_products_cost_price_non_negative"),
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock_non_negative"),
        CheckConstraint("low_stock_threshold >= 0", name="ck_products_threshold_non_negative"),
        Index("ix_products_sku", "sku", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    category = relationship("Category", back_populates="products", lazy="joined")
    supplier = relationship("Supplier", back_populates="products", lazy="joined")
    movements: Mapped[list["StockMovement"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_threshold
