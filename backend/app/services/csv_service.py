"""CSV import/export for products, orders and stock movements.

Import is row-by-row validated: bad rows are skipped and reported, good rows
still import. Exported string cells are sanitized against spreadsheet formula
injection.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation

from fastapi import Response
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, Product
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductRepository
from app.repositories.stock_movement import StockMovementRepository
from app.repositories.supplier import SupplierRepository
from app.schemas.inventory import ProductImportError, ProductImportSummary
from app.schemas.product import ProductCreate
from app.services.exceptions import AppError, ValidationError
from app.services.product_service import ProductService
from app.utils.csv_utils import sanitize_csv_value

IMPORT_COLUMNS = [
    "sku",
    "name",
    "category",
    "supplier",
    "unit_price",
    "cost_price",
    "stock_quantity",
    "low_stock_threshold",
]

MAX_ERRORS_REPORTED = 200
MAX_IMPORT_BYTES = 5 * 1024 * 1024  # guard against oversized uploads


def _parse_decimal(raw: str, *, field: str) -> Decimal:
    text = raw.strip()
    if not text:
        raise ValidationError(f"'{field}' is required.")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"'{field}' is not a valid number (got '{text}').")
    if not value.is_finite():
        raise ValidationError(f"'{field}' must be a finite number.")
    return value


def _parse_int(raw: str, *, field: str) -> int:
    text = raw.strip()
    if not text:
        raise ValidationError(f"'{field}' is required.")
    try:
        return int(text)
    except ValueError:
        raise ValidationError(f"'{field}' must be a whole number (got '{text}').")


def import_products(db: Session, *, content: bytes) -> ProductImportSummary:
    if len(content) > MAX_IMPORT_BYTES:
        raise ValidationError("CSV file is too large (limit: 5 MB).")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"File must be UTF-8 encoded CSV ({exc}).")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationError("CSV file is empty or has no header row.")
    header = [name.strip().lower() for name in reader.fieldnames]
    if len(header) != len(set(header)):
        raise ValidationError("Invalid CSV header: duplicate column names.")
    missing = [column for column in IMPORT_COLUMNS if column not in header]
    if missing:
        raise ValidationError(
            "Invalid CSV header. Missing required columns: " + ", ".join(missing) + "."
        )

    products = ProductService(db)
    categories = CategoryRepository(db)
    suppliers = SupplierRepository(db)

    imported = 0
    skipped = 0
    errors: list[ProductImportError] = []
    seen_skus: set[str] = set()

    for row in reader:
        row_number = reader.line_num
        raw = {key.strip().lower(): (value or "") for key, value in row.items() if key}

        row_errors: list[str] = []
        sku = raw.get("sku", "").strip().upper()
        name = raw.get("name", "").strip()
        if not sku:
            row_errors.append("sku is required")
        elif sku in seen_skus:
            row_errors.append(f"duplicate SKU '{sku}' inside the file")
        if not name:
            row_errors.append("name is required")

        unit_price: Decimal | None = None
        cost_price: Decimal | None = None
        stock_quantity: int | None = None
        threshold: int | None = None
        try:
            unit_price = _parse_decimal(raw.get("unit_price", ""), field="unit_price")
            if raw.get("cost_price", "").strip():
                cost_price = _parse_decimal(raw.get("cost_price", ""), field="cost_price")
            stock_quantity = _parse_int(raw.get("stock_quantity", ""), field="stock_quantity")
            if raw.get("low_stock_threshold", "").strip():
                threshold = _parse_int(raw.get("low_stock_threshold", ""), field="low_stock_threshold")
        except ValidationError as exc:
            row_errors.append(exc.message)

        if unit_price is not None and unit_price < 0:
            row_errors.append("unit_price must be >= 0")
        if cost_price is not None and cost_price < 0:
            row_errors.append("cost_price must be >= 0")
        if stock_quantity is not None and stock_quantity < 0:
            row_errors.append("stock_quantity must be >= 0")
        if threshold is not None and threshold < 0:
            row_errors.append("low_stock_threshold must be >= 0")

        category = categories.get_by_name(raw.get("category", "")) if raw.get("category", "").strip() else None
        if raw.get("category", "").strip() and category is None:
            row_errors.append(f"category '{raw.get('category').strip()}' does not exist")
        supplier = suppliers.get_by_name(raw.get("supplier", "")) if raw.get("supplier", "").strip() else None
        if raw.get("supplier", "").strip() and supplier is None:
            row_errors.append(f"supplier '{raw.get('supplier').strip()}' does not exist")

        if row_errors:
            for message in row_errors:
                if len(errors) < MAX_ERRORS_REPORTED:
                    errors.append(ProductImportError(row=row_number, message=message))
            skipped += 1
            continue

        seen_skus.add(sku)
        try:
            products.create_product(
                ProductCreate(
                    sku=sku,
                    name=name,
                    description=None,
                    category_id=category.id if category else None,
                    supplier_id=supplier.id if supplier else None,
                    unit_price=unit_price,
                    cost_price=cost_price,
                    stock_quantity=stock_quantity or 0,
                    low_stock_threshold=threshold or 0,
                    is_active=True,
                )
            )
            imported += 1
        except (AppError, PydanticValidationError) as exc:
            # Pydantic errors (e.g. >2 decimal places) are row-level problems
            # too — they must skip the row, never crash the whole import.
            seen_skus.discard(sku)
            message = (
                str(exc.message) if isinstance(exc, AppError) else "; ".join(
                    err.get("msg", "invalid value") for err in exc.errors()
                )
            )
            if len(errors) < MAX_ERRORS_REPORTED:
                errors.append(ProductImportError(row=row_number, message=message))
            skipped += 1

    return ProductImportSummary(
        total_rows=imported + skipped,
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


# ---- exports ---------------------------------------------------------------


def _csv_response(rows: list[list], filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([sanitize_csv_value(cell) if isinstance(cell, str) else cell for cell in row])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _fmt_money(value: Decimal | None) -> str:
    return "" if value is None else f"{value:.2f}"


def export_products(db: Session) -> Response:
    products = ProductRepository(db).list_all_for_export()
    rows: list[list] = [["sku", "name", "category", "supplier", "unit_price", "cost_price",
                         "stock_quantity", "low_stock_threshold", "is_active"]]
    for p in products:
        rows.append([
            p.sku,
            p.name,
            p.category.name if p.category else "",
            p.supplier.name if p.supplier else "",
            _fmt_money(p.unit_price),
            _fmt_money(p.cost_price),
            p.stock_quantity,
            p.low_stock_threshold,
            "yes" if p.is_active else "no",
        ])
    return _csv_response(rows, "products.csv")


def export_orders(db: Session) -> Response:
    orders = list(db.execute(select(Order).order_by(Order.created_at.desc())).scalars())
    rows: list[list] = [["order_number", "order_date", "customer", "status", "product_sku",
                         "product_name", "quantity", "unit_price", "line_total", "order_total"]]
    for o in orders:
        if o.items:
            for item in o.items:
                rows.append([
                    o.order_number,
                    o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    o.customer.name,
                    o.status,
                    item.product.sku,
                    item.product.name,
                    item.quantity,
                    _fmt_money(item.unit_price),
                    _fmt_money(item.line_total),
                    _fmt_money(o.total_amount),
                ])
        else:
            rows.append([o.order_number, o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                         o.customer.name, o.status, "", "", "", "", "", _fmt_money(o.total_amount)])
    return _csv_response(rows, "orders.csv")


def export_movements(db: Session) -> Response:
    movements = StockMovementRepository(db).list(
        product_id=None, movement_type=None, offset=0, limit=100_000
    )[0]
    rows: list[list] = [["movement_id", "created_at", "product_sku", "product_name",
                         "movement_type", "quantity", "stock_after", "reference", "note"]]
    for m in movements:
        reference = ""
        if m.reference_type and m.reference_id:
            reference = f"{m.reference_type}:{m.reference_id}"
        rows.append([
            m.id,
            m.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            m.product.sku,
            m.product.name,
            m.movement_type,
            m.quantity,
            m.stock_after,
            reference,
            m.note or "",
        ])
    return _csv_response(rows, "stock_movements.csv")
