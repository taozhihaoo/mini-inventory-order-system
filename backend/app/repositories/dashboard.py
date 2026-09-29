from __future__ import annotations

from sqlalchemy import func, select

from app.models import Order, OrderItem, OrderStatus, Product
from app.repositories.base import BaseRepository


class DashboardRepository(BaseRepository):
    model = Product

    def product_stats(self) -> tuple[int, int, int]:
        """Returns (total, active, low_stock) product counts."""
        total = int(self.db.execute(select(func.count()).select_from(Product)).scalar_one())
        active = int(
            self.db.execute(
                select(func.count()).select_from(Product).where(Product.is_active.is_(True))
            ).scalar_one()
        )
        low = int(
            self.db.execute(
                select(func.count())
                .select_from(Product)
                .where(
                    Product.is_active.is_(True),
                    Product.stock_quantity <= Product.low_stock_threshold,
                )
            ).scalar_one()
        )
        return total, active, low

    def inventory_value(self) -> float:
        """Total stock value at cost price across all products."""
        stmt = select(func.coalesce(func.sum(Product.stock_quantity * Product.cost_price), 0))
        return float(self.db.execute(stmt).scalar_one())

    def order_stats(self) -> tuple[int, float]:
        """Returns (total_orders, sales_amount) where sales counts confirmed+completed."""
        total = int(self.db.execute(select(func.count()).select_from(Order)).scalar_one())
        sales_stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.COMPLETED])
        )
        sales = float(self.db.execute(sales_stmt).scalar_one())
        return total, sales

    def low_stock_products(self, limit: int = 50) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True), Product.stock_quantity <= Product.low_stock_threshold)
            .order_by(Product.stock_quantity.asc(), Product.name)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def recent_orders(self, limit: int = 8) -> list[Order]:
        stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def orders_for_product(self, product_id: int, limit: int = 10) -> list[Order]:
        stmt = (
            select(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(OrderItem.product_id == product_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
