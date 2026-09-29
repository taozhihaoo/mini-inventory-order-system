from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select

from app.models import Order, OrderStatus
from app.repositories.base import BaseRepository, count_rows, escape_like

SORTABLE_FIELDS = {
    "order_number": Order.order_number,
    "total_amount": Order.total_amount,
    "created_at": Order.created_at,
}


class OrderRepository(BaseRepository[Order]):
    model = Order

    def latest_for_prefix(self, prefix: str) -> str | None:
        stmt = (
            select(Order.order_number)
            .where(Order.order_number.like(prefix + "%"))
            .order_by(Order.order_number.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def filter_statement(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        customer_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Select:
        stmt = select(Order)
        if search:
            pattern = f"%{escape_like(search)}%"
            stmt = stmt.where(Order.order_number.ilike(pattern, escape="\\"))
        if status:
            stmt = stmt.where(Order.status == status)
        if customer_id is not None:
            stmt = stmt.where(Order.customer_id == customer_id)
        if date_from is not None:
            stmt = stmt.where(Order.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Order.created_at < date_to)
        return stmt

    def list(
        self,
        *,
        search: str | None,
        status: str | None,
        customer_id: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        sort_by: str,
        sort_dir: str,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        stmt = self.filter_statement(
            search=search,
            status=status,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        column = SORTABLE_FIELDS.get(sort_by, Order.created_at)
        direction = column.desc() if sort_dir == "desc" else column.asc()
        total = count_rows(self.db, stmt)
        rows = (
            self.db.execute(stmt.order_by(direction, Order.id.desc()).offset(offset).limit(limit))
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def count_by_status(self, statuses: tuple[str, ...] = OrderStatus.ALL) -> dict[str, int]:
        stmt = select(Order.status, func.count()).group_by(Order.status)
        result: dict[str, int] = {status: 0 for status in statuses}
        for status, count in self.db.execute(stmt).all():
            result[status] = int(count)
        return result
