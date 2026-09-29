"""Order business logic: lifecycle state machine + transactional stock effects.

Transitions:
    draft     -> confirmed (stock OUT movements, total computed)
    draft     -> cancelled
    confirmed -> completed
    confirmed -> cancelled (stock IN movements to restore)

Everything a transition touches happens in ONE transaction (the request's).
Any failure rolls back completely — no partial stock deduction.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Customer, MovementType, Order, OrderItem, OrderStatus, Product
from app.repositories.order import OrderRepository
from app.schemas.common import Page
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.exceptions import (
    ConflictError,
    InsufficientStockError,
    InvalidStateTransitionError,
    NotFoundError,
    ValidationError,
)
from app.services.inventory_service import InventoryService
from app.services.order_number import next_order_number

MONEY_QUANT = Decimal("0.01")
MAX_NUMBER_RETRIES = 5


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OrderRepository(db)

    # ---- queries ------------------------------------------------------------

    def list_orders(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        customer_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Page[Order]:
        if status is not None and status not in OrderStatus.ALL:
            raise ValidationError(f"Invalid status '{status}'. Allowed: {', '.join(OrderStatus.ALL)}.")
        rows, total = self.repo.list(
            search=search,
            status=status,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page.build(items=rows, total=total, page=page, page_size=page_size)

    def get_order(self, order_id: int) -> Order:
        order = self.repo.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found.")
        return order

    # ---- creation -----------------------------------------------------------

    def create_order(self, data: OrderCreate) -> Order:
        customer = self.db.get(Customer, data.customer_id)
        if customer is None:
            raise NotFoundError(f"Customer {data.customer_id} not found.")
        line_specs = self._validated_lines(data.items)

        for _ in range(MAX_NUMBER_RETRIES):
            order = Order(
                order_number=next_order_number(self.db),
                customer_id=customer.id,
                status=OrderStatus.DRAFT,
                total_amount=Decimal("0.00"),
            )
            total = Decimal("0.00")
            for product, quantity in line_specs:
                unit_price = product.unit_price.quantize(MONEY_QUANT)
                line_total = (unit_price * quantity).quantize(MONEY_QUANT)
                order.items.append(
                    OrderItem(
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total,
                    )
                )
                total += line_total
            order.total_amount = total
            self.db.add(order)
            try:
                self.db.flush()
                return order
            except IntegrityError as exc:
                self.db.rollback()
                if "order_number" not in str(exc.orig):
                    raise
        raise ConflictError("Could not generate a unique order number. Please retry.")

    def _validated_lines(self, items: list[OrderItemCreate]) -> list[tuple[Product, int]]:
        """Validate items, merging duplicate product lines (quantity aggregates)."""
        merged: dict[int, int] = {}
        for item in items:
            merged[item.product_id] = merged.get(item.product_id, 0) + item.quantity
        specs: list[tuple[Product, int]] = []
        for product_id, quantity in merged.items():
            product = self.db.get(Product, product_id)
            if product is None:
                raise NotFoundError(f"Product {product_id} not found.")
            if not product.is_active:
                raise ValidationError(f"Product '{product.sku}' is inactive and cannot be ordered.")
            specs.append((product, quantity))
        return specs

    # ---- lifecycle ----------------------------------------------------------

    def confirm_order(self, order_id: int) -> Order:
        order = self.get_order(order_id)
        self._require_status(order, OrderStatus.DRAFT, "confirmed")

        inventory = InventoryService(self.db)
        demand: dict[int, int] = {}
        for item in order.items:
            demand[item.product_id] = demand.get(item.product_id, 0) + item.quantity

        products: dict[int, Product] = {}
        for product_id, quantity in demand.items():
            product = self.db.get(Product, product_id)
            if product is None:
                raise NotFoundError(f"Product {product_id} on order no longer exists.")
            if not product.is_active:
                raise ValidationError(f"Product '{product.sku}' is inactive and cannot be confirmed.")
            if product.stock_quantity < quantity:
                raise InsufficientStockError(
                    f"Insufficient stock for '{product.sku}': required {quantity}, "
                    f"available {product.stock_quantity}."
                )
            products[product_id] = product

        total = sum((item.line_total for item in order.items), Decimal("0.00"))
        order.total_amount = total.quantize(MONEY_QUANT)

        for item in order.items:
            inventory.record_movement(
                products[item.product_id],
                movement_type=MovementType.OUT,
                change=-item.quantity,
                reference_type="order",
                reference_id=order.id,
                note=f"Order {order.order_number} confirmed",
            )
        order.status = OrderStatus.CONFIRMED
        self.db.flush()
        return order

    def cancel_order(self, order_id: int) -> Order:
        order = self.get_order(order_id)
        if order.status == OrderStatus.DRAFT:
            order.status = OrderStatus.CANCELLED
            self.db.flush()
            return order
        if order.status == OrderStatus.CONFIRMED:
            inventory = InventoryService(self.db)
            for item in order.items:
                product = self.db.get(Product, item.product_id)
                if product is None:  # pragma: no cover - guarded by FK + delete rules
                    raise NotFoundError(f"Product {item.product_id} no longer exists.")
                inventory.record_movement(
                    product,
                    movement_type=MovementType.IN,
                    change=item.quantity,
                    reference_type="order",
                    reference_id=order.id,
                    note=f"Order {order.order_number} cancelled — stock restored",
                )
            order.status = OrderStatus.CANCELLED
            self.db.flush()
            return order
        raise InvalidStateTransitionError(
            f"Order {order.order_number} cannot be cancelled from status '{order.status}'."
        )

    def complete_order(self, order_id: int) -> Order:
        order = self.get_order(order_id)
        self._require_status(order, OrderStatus.CONFIRMED, "completed")
        order.status = OrderStatus.COMPLETED
        self.db.flush()
        return order

    @staticmethod
    def _require_status(order: Order, expected: str, action: str) -> None:
        if order.status != expected:
            raise InvalidStateTransitionError(
                f"Only {expected} orders can be {action} (order {order.order_number} is {order.status})."
            )
