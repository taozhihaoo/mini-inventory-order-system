from __future__ import annotations

from sqlalchemy import func, select

from app.models import Product, Supplier
from app.repositories.base import BaseRepository, count_rows, escape_like


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    def get_by_name(self, name: str) -> Supplier | None:
        stmt = select(Supplier).where(func.lower(Supplier.name) == name.strip().lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self, *, search: str | None, offset: int, limit: int
    ) -> tuple[list[tuple[Supplier, int]], int]:
        product_count = func.count(Product.id).label("product_count")
        stmt = (
            select(Supplier, product_count)
            .outerjoin(Product, Product.supplier_id == Supplier.id)
            .group_by(Supplier.id)
        )
        if search:
            pattern = f"%{escape_like(search)}%"
            stmt = stmt.where(Supplier.name.ilike(pattern, escape="\\"))
        total = count_rows(self.db, stmt)
        rows = (
            self.db.execute(stmt.order_by(Supplier.name).offset(offset).limit(limit)).all()
        )
        return rows, int(total)

    def count_products(self, supplier_id: int) -> int:
        stmt = select(func.count(Product.id)).where(Product.supplier_id == supplier_id)
        return int(self.db.execute(stmt).scalar_one())
