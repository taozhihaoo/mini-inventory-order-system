from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(tags=["customers"])


def _to_out(service: CustomerService, customer) -> CustomerOut:
    out = CustomerOut.model_validate(customer)
    out.order_count = service.order_count(customer.id)
    return out


@router.get("/customers", response_model=Page[CustomerOut])
def list_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
):
    service = CustomerService(db)
    result = service.list_customers(search=search, page=page, page_size=page_size)
    items = [_to_out(service, c) for c in result.items]
    return Page.build(items=items, total=result.total, page=result.page, page_size=result.page_size)


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    service = CustomerService(db)
    return _to_out(service, service.create_customer(data))


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    service = CustomerService(db)
    return _to_out(service, service.get_customer(customer_id))


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    service = CustomerService(db)
    return _to_out(service, service.update_customer(customer_id, data))


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    CustomerService(db).delete_customer(customer_id)
