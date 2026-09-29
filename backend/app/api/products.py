from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.schemas.order import OrderListOut
from app.services.csv_service import export_products, import_products
from app.services.product_service import ProductService

router = APIRouter(tags=["products"])

# NOTE: static paths (export/import) are declared BEFORE /{product_id} routes so
# FastAPI does not try to parse "export.csv" as an int path parameter.

SORT_HELP = "name | sku | unit_price | cost_price | stock_quantity | created_at"


@router.get("/products/export.csv")
def products_export_csv(db: Session = Depends(get_db)):
    return export_products(db)


@router.post("/products/import", response_model=dict)
async def products_import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    summary = import_products(db, content=content)
    return summary.model_dump()


@router.get("/products", response_model=Page[ProductOut])
def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    category_id: int | None = Query(default=None, ge=1),
    supplier_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = Query(default=None),
    low_stock: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at", description=SORT_HELP),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    result = ProductService(db).list_products(
        search=search,
        category_id=category_id,
        supplier_id=supplier_id,
        is_active=is_active,
        low_stock=low_stock,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return result


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    return ProductService(db).create_product(data)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return ProductService(db).get_product(product_id)


@router.get("/products/{product_id}/orders", response_model=list[OrderListOut])
def product_orders(
    product_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return ProductService(db).get_recent_orders(product_id, limit=limit)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    return ProductService(db).update_product(product_id, data)


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    ProductService(db).delete_product(product_id)
