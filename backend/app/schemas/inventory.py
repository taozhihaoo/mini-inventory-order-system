from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductBrief


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StockOperationCreate(BaseModel):
    """Stock In / Stock Out payload."""

    quantity: int = Field(gt=0, le=1_000_000)
    note: str | None = Field(default=None, max_length=500)


class StockAdjustCreate(BaseModel):
    """Stock Adjustment payload: set an absolute counted quantity."""

    new_quantity: int = Field(ge=0, le=1_000_000)
    note: str | None = Field(default=None, max_length=500)


class StockOperationResult(BaseModel):
    movement_type: str
    product_id: int
    sku: str
    name: str
    previous_quantity: int
    new_quantity: int
    change: int
    movement_id: int


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product: ProductBrief | None = None
    movement_type: str
    quantity: int
    stock_after: int
    reference_type: str | None = None
    reference_id: int | None = None
    note: str | None = None
    created_at: datetime


class LowStockItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    stock_quantity: int
    low_stock_threshold: int
    category_id: int | None = None
    category: CategoryBrief | None = None


class ProductImportError(BaseModel):
    row: int
    message: str


class ProductImportSummary(BaseModel):
    total_rows: int
    imported: int
    skipped: int
    errors: list[ProductImportError]
