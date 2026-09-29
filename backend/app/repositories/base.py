"""Shared repository helpers (query layer only — no business rules)."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: int) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()

    def count_all(self) -> int:
        return self.db.execute(select(func.count()).select_from(self.model)).scalar_one()


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so user search input matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def apply_pagination(stmt: Select, offset: int, limit: int) -> Select:
    return stmt.offset(offset).limit(limit)


def count_rows(db: Session, stmt: Select) -> int:
    return db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
