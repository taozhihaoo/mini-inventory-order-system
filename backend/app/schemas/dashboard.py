from __future__ import annotations

from pydantic import BaseModel

from app.schemas.inventory import MovementOut
from app.schemas.order import OrderListOut
from app.schemas.product import ProductOut


class DashboardSummary(BaseModel):
    total_products: int
    active_products: int
    low_stock_products: int
    inventory_value: float
    total_orders: int
    confirmed_orders: int
    completed_orders: int
    sales_amount: float
    recent_orders: list[OrderListOut]
    low_stock_list: list[ProductOut]
    recent_movements: list[MovementOut]
