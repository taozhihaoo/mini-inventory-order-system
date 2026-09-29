"""Dashboard aggregation logic."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.dashboard import DashboardRepository
from app.repositories.order import OrderRepository
from app.repositories.stock_movement import StockMovementRepository
from app.schemas.dashboard import DashboardSummary

MONEY_QUANT = Decimal("0.01")


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DashboardRepository(db)
        self.movements = StockMovementRepository(db)
        self.orders = OrderRepository(db)

    def summary(self) -> DashboardSummary:
        total_products, active_products, low_stock_count = self.repo.product_stats()
        total_orders, sales_amount = self.repo.order_stats()
        status_counts = self.orders.count_by_status()

        return DashboardSummary(
            total_products=total_products,
            active_products=active_products,
            low_stock_products=low_stock_count,
            inventory_value=round(self.repo.inventory_value(), 2),
            total_orders=total_orders,
            confirmed_orders=status_counts.get("confirmed", 0),
            completed_orders=status_counts.get("completed", 0),
            sales_amount=round(sales_amount, 2),
            recent_orders=self.repo.recent_orders(limit=8),
            low_stock_list=self.repo.low_stock_products(limit=50),
            recent_movements=self.movements.recent(limit=8),
        )
