from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page
from app.services.category_service import CategoryService

router = APIRouter(tags=["categories"])


def _to_out(service: CategoryService, category) -> CategoryOut:
    out = CategoryOut.model_validate(category)
    out.product_count = service.product_count(category.id)
    return out


@router.get("/categories", response_model=Page[CategoryOut])
def list_categories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    result = service.list_categories(search=search, page=page, page_size=page_size)
    items = [_to_out(service, c) for c in result.items]
    return Page.build(items=items, total=result.total, page=result.page, page_size=result.page_size)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    service = CategoryService(db)
    return _to_out(service, service.create_category(data))


@router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    service = CategoryService(db)
    return _to_out(service, service.get_category(category_id))


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    service = CategoryService(db)
    return _to_out(service, service.update_category(category_id, data))


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    CategoryService(db).delete_category(category_id)
