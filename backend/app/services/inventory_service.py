"""Inventory business logic — the ONLY place stock_quantity is ever mutated.

Every stock change goes through record_movement(), which updates the product
and writes a StockMovement atomically inside the caller's transaction. No
half-completed states are possible: if anything raises, get_db() rolls the
whole request back.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import MovementType, Product, StockMovement
from app.repositories.product import ProductRepository
from app.repositories.stock_movement import StockMovementRepository
from app.schemas.inventory import StockAdjustCreate, StockOperationCreate, StockOperationResult
from app.schemas.common import Page
from app.services.exceptions import InsufficientStockError, NotFoundError, ValidationError


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.movements = StockMovementRepository(db)

    # ---- single choke point -------------------------------------------------

    def record_movement(
        self,
        product: Product,
        *,
        movement_type: str,
        change: int,
        reference_type: str | None = None,
        reference_id: int | None = None,
        note: str | None = None,
    ) -> StockMovement:
        """Apply a signed stock change and record the movement. Raises on negative stock."""
        if change == 0:
            raise ValidationError("Stock change must not be zero.")
        new_stock = product.stock_quantity + change
        if new_stock < 0:
            raise InsufficientStockError(
                f"Stock for '{product.sku}' would become negative ({new_stock})."
            )
        product.stock_quantity = new_stock
        movement = StockMovement(
            product_id=product.id,
            movement_type=movement_type,
            quantity=abs(change) if movement_type in (MovementType.IN, MovementType.OUT) else change,
            stock_after=new_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
        )
        self.db.add(movement)
        self.db.flush()
        return movement

    # ---- public operations --------------------------------------------------

    def _get_product(self, product_id: int) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")
        return product

    def stock_in(self, product_id: int, data: StockOperationCreate) -> StockOperationResult:
        product = self._get_product(product_id)
        previous = product.stock_quantity
        movement = self.record_movement(
            product, movement_type=MovementType.IN, change=data.quantity, note=data.note
        )
        return StockOperationResult(
            movement_type=MovementType.IN,
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            previous_quantity=previous,
            new_quantity=product.stock_quantity,
            change=data.quantity,
            movement_id=movement.id,
        )

    def stock_out(self, product_id: int, data: StockOperationCreate) -> StockOperationResult:
        product = self._get_product(product_id)
        previous = product.stock_quantity
        if data.quantity > previous:
            raise InsufficientStockError(
                f"Insufficient stock for '{product.sku}': requested {data.quantity}, available {previous}."
            )
        movement = self.record_movement(
            product, movement_type=MovementType.OUT, change=-data.quantity, note=data.note
        )
        return StockOperationResult(
            movement_type=MovementType.OUT,
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            previous_quantity=previous,
            new_quantity=product.stock_quantity,
            change=-data.quantity,
            movement_id=movement.id,
        )

    def stock_adjust(self, product_id: int, data: StockAdjustCreate) -> StockOperationResult:
        product = self._get_product(product_id)
        previous = product.stock_quantity
        change = data.new_quantity - previous
        if change == 0:
            raise ValidationError(
                f"New quantity ({data.new_quantity}) equals current stock for '{product.sku}'."
            )
        movement = self.record_movement(
            product, movement_type=MovementType.ADJUSTMENT, change=change, note=data.note
        )
        return StockOperationResult(
            movement_type=MovementType.ADJUSTMENT,
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            previous_quantity=previous,
            new_quantity=product.stock_quantity,
            change=change,
            movement_id=movement.id,
        )

    # ---- queries ------------------------------------------------------------

    def list_product_movements(self, product_id: int, *, page: int, page_size: int) -> Page[StockMovement]:
        self._get_product(product_id)
        rows, total = self.movements.list(
            product_id=product_id, movement_type=None, offset=(page - 1) * page_size, limit=page_size
        )
        return Page.build(items=rows, total=total, page=page, page_size=page_size)

    def list_movements(
        self, *, product_id: int | None, movement_type: str | None, page: int, page_size: int
    ) -> Page[StockMovement]:
        if movement_type is not None and movement_type not in MovementType.ALL:
            raise ValidationError(
                f"Invalid movement type '{movement_type}'. Allowed: {', '.join(MovementType.ALL)}."
            )
        rows, total = self.movements.list(
            product_id=product_id,
            movement_type=movement_type,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page.build(items=rows, total=total, page=page, page_size=page_size)

    def list_low_stock(self) -> list[Product]:
        stmt = (
            self.products.filter_statement(is_active=True, low_stock=True)
            .order_by(Product.stock_quantity.asc(), Product.name)
        )
        return list(self.db.execute(stmt).scalars().all())
