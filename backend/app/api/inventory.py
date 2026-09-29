from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.inventory import (
    MovementOut,
    StockAdjustCreate,
    StockOperationCreate,
    StockOperationResult,
)
from app.schemas.product import ProductOut
from app.services.csv_service import export_movements
from app.services.inventory_service import InventoryService

router = APIRouter(tags=["inventory"])


@router.get("/inventory/low-stock", response_model=list[ProductOut])
def low_stock(db: Session = Depends(get_db)):
    return InventoryService(db).list_low_stock()


@router.get("/inventory/movements/export.csv")
def movements_export_csv(db: Session = Depends(get_db)):
    return export_movements(db)


@router.get("/inventory/movements", response_model=Page[MovementOut])
def list_movements(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    product_id: int | None = Query(default=None, ge=1),
    movement_type: str | None = Query(default=None, description="IN | OUT | ADJUSTMENT"),
    db: Session = Depends(get_db),
):
    return InventoryService(db).list_movements(
        product_id=product_id, movement_type=movement_type, page=page, page_size=page_size
    )


@router.post("/products/{product_id}/stock/in", response_model=StockOperationResult)
def stock_in(product_id: int, data: StockOperationCreate, db: Session = Depends(get_db)):
    return InventoryService(db).stock_in(product_id, data)


@router.post("/products/{product_id}/stock/out", response_model=StockOperationResult)
def stock_out(product_id: int, data: StockOperationCreate, db: Session = Depends(get_db)):
    return InventoryService(db).stock_out(product_id, data)


@router.post("/products/{product_id}/stock/adjust", response_model=StockOperationResult)
def stock_adjust(product_id: int, data: StockAdjustCreate, db: Session = Depends(get_db)):
    return InventoryService(db).stock_adjust(product_id, data)


@router.get("/products/{product_id}/stock/movements", response_model=Page[MovementOut])
def product_movements(
    product_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return InventoryService(db).list_product_movements(product_id, page=page, page_size=page_size)
