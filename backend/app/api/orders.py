from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderListOut, OrderOut, OrderStatusInfo
from app.services.order_service import OrderService

router = APIRouter(tags=["orders"])

SORT_HELP = "order_number | total_amount | created_at"


@router.get("/orders/export.csv")
def orders_export_csv(db: Session = Depends(get_db)):
    from app.services.csv_service import export_orders

    return export_orders(db)


def _as_datetime_start(day: date) -> datetime:
    return datetime.combine(day, time.min)


def _as_datetime_end_exclusive(day: date) -> datetime:
    from datetime import timedelta

    return datetime.combine(day + timedelta(days=1), time.min)


@router.get("/orders", response_model=Page[OrderListOut])
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=64, description="Order number search"),
    status: str | None = Query(default=None, description="draft | confirmed | completed | cancelled"),
    customer_id: int | None = Query(default=None, ge=1),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sort_by: str = Query(default="created_at", description=SORT_HELP),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    return OrderService(db).list_orders(
        search=search,
        status=status,
        customer_id=customer_id,
        date_from=_as_datetime_start(date_from) if date_from else None,
        date_to=_as_datetime_end_exclusive(date_to) if date_to else None,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    return OrderService(db).create_order(data)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return OrderService(db).get_order(order_id)


@router.post("/orders/{order_id}/confirm", response_model=OrderStatusInfo)
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    order = OrderService(db).confirm_order(order_id)
    return OrderStatusInfo(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        previous_status="draft",
    )


@router.post("/orders/{order_id}/cancel", response_model=OrderStatusInfo)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    previous_status = service.get_order(order_id).status
    order = service.cancel_order(order_id)
    return OrderStatusInfo(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        previous_status=previous_status,
    )


@router.post("/orders/{order_id}/complete", response_model=OrderStatusInfo)
def complete_order(order_id: int, db: Session = Depends(get_db)):
    service = OrderService(db)
    previous_status = service.get_order(order_id).status
    order = service.complete_order(order_id)
    return OrderStatusInfo(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        previous_status=previous_status,
    )
