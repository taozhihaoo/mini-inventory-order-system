"""Product business logic."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import MovementType, Product
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductRepository
from app.repositories.supplier import SupplierRepository
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.exceptions import DuplicateError, NotFoundError, ReferencedError
from app.services.inventory_service import InventoryService

MONEY_QUANT = Decimal("0.01")


def _money(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(MONEY_QUANT)


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ProductRepository(db)
        self.categories = CategoryRepository(db)
        self.suppliers = SupplierRepository(db)

    # ---- validation helpers -------------------------------------------------

    def _validate_references(
        self, category_id: int | None, supplier_id: int | None
    ) -> None:
        if category_id is not None and self.categories.get(category_id) is None:
            raise NotFoundError(f"Category {category_id} not found.")
        if supplier_id is not None and self.suppliers.get(supplier_id) is None:
            raise NotFoundError(f"Supplier {supplier_id} not found.")

    def _ensure_sku_free(self, sku: str, *, exclude_id: int | None = None) -> str:
        normalized = sku.strip().upper()
        existing = self.repo.get_by_sku(normalized)
        if existing and existing.id != exclude_id:
            raise DuplicateError(f"SKU '{normalized}' already exists.")
        return normalized

    # ---- CRUD ---------------------------------------------------------------

    def list_products(
        self,
        *,
        search: str | None = None,
        category_id: int | None = None,
        supplier_id: int | None = None,
        is_active: bool | None = None,
        low_stock: bool | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Page[Product]:
        rows, total = self.repo.list(
            search=search,
            category_id=category_id,
            supplier_id=supplier_id,
            is_active=is_active,
            low_stock=low_stock,
            sort_by=sort_by,
            sort_dir=sort_dir,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page.build(items=rows, total=total, page=page, page_size=page_size)

    def get_product(self, product_id: int) -> Product:
        product = self.repo.get(product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")
        return product

    def create_product(self, data: ProductCreate) -> Product:
        sku = self._ensure_sku_free(data.sku)
        self._validate_references(data.category_id, data.supplier_id)
        product = Product(
            sku=sku,
            name=data.name.strip(),
            description=data.description,
            category_id=data.category_id,
            supplier_id=data.supplier_id,
            unit_price=_money(data.unit_price),
            cost_price=_money(data.cost_price),
            stock_quantity=0,
            low_stock_threshold=data.low_stock_threshold,
            is_active=data.is_active,
        )
        self.repo.add(product)
        if data.stock_quantity > 0:
            InventoryService(self.db).record_movement(
                product,
                movement_type=MovementType.IN,
                change=data.stock_quantity,
                note="Initial stock on product creation",
            )
        return product

    def update_product(self, product_id: int, data: ProductUpdate) -> Product:
        product = self.get_product(product_id)
        changes = data.model_dump(exclude_unset=True)
        if "sku" in changes and changes["sku"] is not None:
            product.sku = self._ensure_sku_free(changes["sku"], exclude_id=product.id)
        if "name" in changes and changes["name"] is not None:
            product.name = changes["name"].strip()
        if "category_id" in changes:
            self._validate_references(changes["category_id"], None)
            product.category_id = changes["category_id"]
        if "supplier_id" in changes:
            self._validate_references(None, changes["supplier_id"])
            product.supplier_id = changes["supplier_id"]
        for field in ("description", "unit_price", "cost_price", "low_stock_threshold", "is_active"):
            if field in changes:
                value = changes[field]
                if field in ("unit_price", "cost_price"):
                    value = _money(value)
                setattr(product, field, value)
        self.db.flush()
        return product

    def delete_product(self, product_id: int) -> None:
        product = self.get_product(product_id)
        has_movements = len(product.movements) > 0
        has_order_items = self.repo.count_order_items(product.id) > 0
        if has_movements or has_order_items:
            raise ReferencedError(
                f"Product '{product.sku}' has stock movements or order history and cannot be deleted. "
                "Deactivate it instead."
            )
        self.repo.delete(product)

    def get_recent_orders(self, product_id: int, *, limit: int = 10):
        """Orders that contain this product, newest first (for the detail page)."""
        from app.repositories.dashboard import DashboardRepository

        self.get_product(product_id)
        return DashboardRepository(self.db).orders_for_product(product_id, limit=limit)
