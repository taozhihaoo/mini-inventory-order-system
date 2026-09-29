from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryOut
from app.schemas.supplier import SupplierOut

SKU_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$"

Money = Decimal


class ProductBase(BaseModel):
    sku: str = Field(pattern=SKU_PATTERN, description="2-64 chars: letters, digits, dash, underscore")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: Money = Field(ge=0, le=Decimal("99999999.99"), max_digits=12, decimal_places=2)
    cost_price: Money | None = Field(default=None, ge=0, le=Decimal("99999999.99"), max_digits=12, decimal_places=2)
    low_stock_threshold: int = Field(default=0, ge=0, le=1_000_000)
    is_active: bool = True


class ProductCreate(ProductBase):
    stock_quantity: int = Field(default=0, ge=0, le=1_000_000)


class ProductUpdate(BaseModel):
    """Note: stock_quantity is intentionally NOT updatable here.

    Stock may only change through the inventory endpoints so that every change
    produces a StockMovement and stays transactional.
    """

    sku: str | None = Field(default=None, pattern=SKU_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: Money | None = Field(default=None, ge=0, le=Decimal("99999999.99"), max_digits=12, decimal_places=2)
    cost_price: Money | None = Field(default=None, ge=0, le=Decimal("99999999.99"), max_digits=12, decimal_places=2)
    low_stock_threshold: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: bool | None = None


class ProductOut(ProductBase):
    """Response model — money is serialized as JSON numbers (float), not strings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_quantity: int
    is_low_stock: bool
    unit_price: float
    cost_price: float | None = None
    category: CategoryOut | None = None
    supplier: SupplierOut | None = None
    created_at: datetime
    updated_at: datetime


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    unit_price: float
