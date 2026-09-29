from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate
from app.services.supplier_service import SupplierService

router = APIRouter(tags=["suppliers"])


def _to_out(service: SupplierService, supplier) -> SupplierOut:
    out = SupplierOut.model_validate(supplier)
    out.product_count = service.product_count(supplier.id)
    return out


@router.get("/suppliers", response_model=Page[SupplierOut])
def list_suppliers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
):
    service = SupplierService(db)
    result = service.list_suppliers(search=search, page=page, page_size=page_size)
    items = [_to_out(service, s) for s in result.items]
    return Page.build(items=items, total=result.total, page=result.page, page_size=result.page_size)


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    service = SupplierService(db)
    return _to_out(service, service.create_supplier(data))


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    service = SupplierService(db)
    return _to_out(service, service.get_supplier(supplier_id))


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, data: SupplierUpdate, db: Session = Depends(get_db)):
    service = SupplierService(db)
    return _to_out(service, service.update_supplier(supplier_id, data))


@router.delete("/suppliers/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    SupplierService(db).delete_supplier(supplier_id)
