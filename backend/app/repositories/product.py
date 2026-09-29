from __future__ import annotations

from sqlalchemy import Select, func, or_, select

from app.models import OrderItem, Product
from app.repositories.base import BaseRepository, count_rows, escape_like

SORTABLE_FIELDS = {
    "name": Product.name,
    "sku": Product.sku,
    "unit_price": Product.unit_price,
    "cost_price": Product.cost_price,
    "stock_quantity": Product.stock_quantity,
    "created_at": Product.created_at,
}


class ProductRepository(BaseRepository[Product]):
    model = Product

    def get_by_sku(self, sku: str) -> Product | None:
        stmt = select(Product).where(func.upper(Product.sku) == sku.strip().upper())
        return self.db.execute(stmt).scalar_one_or_none()

    def filter_statement(
        self,
        *,
        search: str | None = None,
        category_id: int | None = None,
        supplier_id: int | None = None,
        is_active: bool | None = None,
        low_stock: bool | None = None,
    ) -> Select:
        stmt = select(Product)
        if search:
            pattern = f"%{escape_like(search)}%"
            stmt = stmt.where(or_(Product.name.ilike(pattern, escape="\\"), Product.sku.ilike(pattern, escape="\\")))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if supplier_id is not None:
            stmt = stmt.where(Product.supplier_id == supplier_id)
        if is_active is not None:
            stmt = stmt.where(Product.is_active == is_active)
        if low_stock is not None:
            if low_stock:
                stmt = stmt.where(Product.stock_quantity <= Product.low_stock_threshold)
            else:
                stmt = stmt.where(Product.stock_quantity > Product.low_stock_threshold)
        return stmt

    def list(
        self,
        *,
        search: str | None,
        category_id: int | None,
        supplier_id: int | None,
        is_active: bool | None,
        low_stock: bool | None,
        sort_by: str,
        sort_dir: str,
        offset: int,
        limit: int,
    ) -> tuple[list[Product], int]:
        stmt = self.filter_statement(
            search=search,
            category_id=category_id,
            supplier_id=supplier_id,
            is_active=is_active,
            low_stock=low_stock,
        )
        column = SORTABLE_FIELDS.get(sort_by, Product.created_at)
        direction = column.desc() if sort_dir == "desc" else column.asc()
        total = count_rows(self.db, stmt)
        rows = (
            self.db.execute(stmt.order_by(direction, Product.id.asc()).offset(offset).limit(limit))
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def list_all_for_export(self) -> list[Product]:
        stmt = self.filter_statement().order_by(Product.sku)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_skus(self, skus: list[str]) -> dict[str, Product]:
        if not skus:
            return {}
        stmt = select(Product).where(func.upper(Product.sku).in_([s.upper() for s in skus]))
        return {p.sku.upper(): p for p in self.db.execute(stmt).scalars().all()}

    def count_order_items(self, product_id: int) -> int:
        stmt = select(func.count(OrderItem.id)).where(OrderItem.product_id == product_id)
        return int(self.db.execute(stmt).scalar_one())
