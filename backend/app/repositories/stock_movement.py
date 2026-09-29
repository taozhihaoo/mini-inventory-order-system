from __future__ import annotations

from sqlalchemy import select

from app.models import StockMovement
from app.repositories.base import BaseRepository, count_rows


class StockMovementRepository(BaseRepository[StockMovement]):
    model = StockMovement

    def list_for_product(self, *, product_id: int, offset: int, limit: int) -> list[StockMovement]:
        stmt = (
            select(StockMovement)
            .where(StockMovement.product_id == product_id)
            .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list(
        self,
        *,
        product_id: int | None,
        movement_type: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[StockMovement], int]:
        stmt = select(StockMovement)
        if product_id is not None:
            stmt = stmt.where(StockMovement.product_id == product_id)
        if movement_type:
            stmt = stmt.where(StockMovement.movement_type == movement_type)
        total = count_rows(self.db, stmt)
        rows = (
            self.db.execute(
                stmt.order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def recent(self, limit: int = 8) -> list[StockMovement]:
        stmt = (
            select(StockMovement)
            .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
