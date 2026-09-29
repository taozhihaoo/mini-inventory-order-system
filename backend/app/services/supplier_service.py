"""Supplier business logic."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Supplier
from app.repositories.supplier import SupplierRepository
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.exceptions import NotFoundError, ReferencedError


class SupplierService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SupplierRepository(db)

    def list_suppliers(self, *, search: str | None, page: int, page_size: int) -> Page[Supplier]:
        rows, total = self.repo.list(search=search, offset=(page - 1) * page_size, limit=page_size)
        items = [row[0] for row in rows]
        return Page.build(items=items, total=total, page=page, page_size=page_size)

    def get_supplier(self, supplier_id: int) -> Supplier:
        supplier = self.repo.get(supplier_id)
        if supplier is None:
            raise NotFoundError(f"Supplier {supplier_id} not found.")
        return supplier

    def create_supplier(self, data: SupplierCreate) -> Supplier:
        return self.repo.add(
            Supplier(
                name=data.name.strip(),
                email=data.email,
                phone=data.phone,
                notes=data.notes,
            )
        )

    def update_supplier(self, supplier_id: int, data: SupplierUpdate) -> Supplier:
        supplier = self.get_supplier(supplier_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            supplier.name = changes["name"].strip()
        for field in ("email", "phone", "notes"):
            if field in changes:
                setattr(supplier, field, changes[field])
        self.db.flush()
        return supplier

    def delete_supplier(self, supplier_id: int) -> None:
        supplier = self.get_supplier(supplier_id)
        used_by = self.repo.count_products(supplier.id)
        if used_by:
            raise ReferencedError(
                f"Supplier '{supplier.name}' is used by {used_by} product(s) and cannot be deleted."
            )
        self.repo.delete(supplier)

    def product_count(self, supplier_id: int) -> int:
        self.get_supplier(supplier_id)
        return self.repo.count_products(supplier_id)
