from __future__ import annotations

from sqlalchemy import func, select

from app.models import Customer, Order
from app.repositories.base import BaseRepository, count_rows, escape_like


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    def list(
        self, *, search: str | None, offset: int, limit: int
    ) -> tuple[list[tuple[Customer, int]], int]:
        order_count = func.count(Order.id).label("order_count")
        stmt = (
            select(Customer, order_count)
            .outerjoin(Order, Order.customer_id == Customer.id)
            .group_by(Customer.id)
        )
        if search:
            pattern = f"%{escape_like(search)}%"
            stmt = stmt.where(
                Customer.name.ilike(pattern, escape="\\") | Customer.email.ilike(pattern, escape="\\")
            )
        total = count_rows(self.db, stmt)
        rows = self.db.execute(stmt.order_by(Customer.name).offset(offset).limit(limit)).all()
        return rows, int(total)

    def count_orders(self, customer_id: int) -> int:
        stmt = select(func.count(Order.id)).where(Order.customer_id == customer_id)
        return int(self.db.execute(stmt).scalar_one())
