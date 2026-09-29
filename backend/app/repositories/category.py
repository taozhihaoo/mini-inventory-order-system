from __future__ import annotations

from sqlalchemy import func, select

from app.models import Category, Product
from app.repositories.base import BaseRepository, escape_like


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_name(self, name: str) -> Category | None:
        stmt = select(Category).where(func.lower(Category.name) == name.strip().lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *, search: str | None, offset: int, limit: int) -> tuple[list[tuple[Category, int]], int]:
        stmt = (
            select(Category, func.count(Product.id))
            .outerjoin(Product, Product.category_id == Category.id)
            .group_by(Category.id)
        )
        if search:
            pattern = f"%{escape_like(search)}%"
            stmt = stmt.where(Category.name.ilike(pattern, escape="\\"))
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = (
            self.db.execute(stmt.order_by(Category.name).offset(offset).limit(limit)).all()
        )
        return rows, int(total)

    def count_products(self, category_id: int) -> int:
        stmt = select(func.count(Product.id)).where(Product.category_id == category_id)
        return int(self.db.execute(stmt).scalar_one())
