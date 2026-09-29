from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.customer import CustomerBrief
from app.schemas.product import ProductBrief


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=1_000_000)


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product: ProductBrief
    quantity: int
    unit_price: float
    line_total: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    customer_id: int
    customer: CustomerBrief
    status: str
    total_amount: float
    items: list[OrderItemOut]
    created_at: datetime
    updated_at: datetime


class OrderListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    customer_id: int
    customer: CustomerBrief
    status: str
    total_amount: float
    item_count: int
    created_at: datetime
    updated_at: datetime


class OrderStatusInfo(BaseModel):
    id: int
    order_number: str
    status: str
    previous_status: str
