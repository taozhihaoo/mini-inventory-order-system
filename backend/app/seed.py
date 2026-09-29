"""Seed the database with fictional demo data.

Usage (from backend/):
    python -m app.seed            # seed only if database is empty
    python -m app.seed --reset    # delete the SQLite file, recreate schema, seed

All data is fictional. Guarantees after seeding:
    - 5 categories, 4 suppliers, 8 customers, 12 products
    - 3 low-stock products (one out of stock)
    - 12 orders: completed / confirmed / cancelled / draft, all with items
    - stock movements: initial IN per product, OUT on confirmed orders,
      IN on the cancelled confirmed order, ADJUSTMENT rows when applicable
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from decimal import Decimal

from app.database import SessionLocal, is_sqlite
from app.config import settings
from app.migrations_runner import run_migrations
from app.models import Customer, Order, OrderStatus, Product, StockMovement
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.schemas.customer import CustomerCreate
from app.schemas.order import OrderCreate, OrderItemCreate
from app.schemas.product import ProductCreate
from app.utils.time import utcnow

M = Decimal


def _reset_sqlite_file() -> None:
    url = settings.database_url
    if not is_sqlite(url) or ":memory:" in url:
        print("DATABASE_URL is not a file-based SQLite database; skipping file reset.")
        return
    from sqlalchemy.engine import make_url

    database = make_url(url).database or ""
    if database.strip() and database != ":memory:":
        import os

        if os.path.exists(database):
            os.remove(database)
            print(f"Deleted database file: {database}")


def seed() -> None:
    run_migrations()
    db = SessionLocal()
    try:
        product_count = db.query(Product).count()
        if product_count > 0:
            print(f"Database already contains {product_count} products.")
            print("Run `python -m app.seed --reset` to rebuild the demo data.")
            return

        categories = {}
        for name, description in [
            ("Lighting", "Desk and floor lamps"),
            ("Furniture", "Desks, shelves and chairs"),
            ("Stationery", "Notebooks and writing supplies"),
            ("Kitchen & Dining", "Mugs, boards and tableware"),
            ("Storage", "Bins and organizers"),
        ]:
            from app.schemas.category import CategoryCreate
            from app.services.category_service import CategoryService

            categories[name] = CategoryService(db).create_category(
                CategoryCreate(name=name, description=description)
            )

        suppliers = {}
        for name, email, phone in [
            ("Bright Source Trading Co.", "sales@brightsource.example.com", "555-0101"),
            ("Northwood Wholesale", "orders@northwood.example.com", "555-0102"),
            ("Casa Craft Supply", "hello@casacraft.example.com", "555-0103"),
            ("Paper Trail Logistics", "contact@papertrail.example.com", "555-0104"),
        ]:
            from app.schemas.supplier import SupplierCreate
            from app.services.supplier_service import SupplierService

            suppliers[name] = SupplierService(db).create_supplier(
                SupplierCreate(name=name, email=email, phone=phone, notes=None)
            )

        customer_names = [
            "Ava Thompson", "Liam Rodriguez", "Maya Chen", "Noah Bennett",
            "Sofia Petrov", "Ethan Walker", "Isla O'Connor", "Lucas Meyer",
        ]
        customers = []
        for name in customer_names:
            customers.append(
                CustomerService(db).create_customer(
                    CustomerCreate(
                        name=name,
                        email=f"{name.split()[0].lower()}@example.com",
                        phone=f"555-02{len(customers) + 10}",
                        notes=None,
                    )
                )
            )

        product_service = ProductService(db)
        products = {}
        catalog = [
            # sku, name, category, supplier, unit, cost, stock, threshold
            ("LMP-1001", "Aurora Desk Lamp", "Lighting", "Bright Source Trading Co.", "39.90", "22.50", 24, 6),
            ("LMP-1002", "Aurora Floor Lamp", "Lighting", "Bright Source Trading Co.", "89.00", "51.00", 9, 4),
            ("LMP-1003", "Nordic Table Lamp", "Lighting", "Casa Craft Supply", "45.50", "26.00", 3, 5),
            ("FUR-2001", "Oak Study Desk", "Furniture", "Northwood Wholesale", "249.00", "158.00", 7, 2),
            ("FUR-2002", "Pine Bookshelf", "Furniture", "Northwood Wholesale", "129.00", "74.00", 12, 3),
            ("FUR-2003", "Mesh Office Chair", "Furniture", "Northwood Wholesale", "159.00", "96.00", 5, 5),
            ("STA-3001", "Linen Notebook A5", "Stationery", "Paper Trail Logistics", "6.90", "2.80", 120, 30),
            ("STA-3002", "Gel Pen 12-pack", "Stationery", "Paper Trail Logistics", "9.50", "3.60", 85, 20),
            ("STA-3003", "Walnut Pen Holder", "Stationery", "Casa Craft Supply", "14.90", "6.20", 0, 10),
            ("KIT-4001", "Ceramic Mug Set", "Kitchen & Dining", "Casa Craft Supply", "24.00", "11.00", 32, 8),
            ("KIT-4002", "Bamboo Cutting Board", "Kitchen & Dining", "Northwood Wholesale", "19.90", "8.40", 41, 10),
            ("STO-5001", "Stackable Storage Bin", "Storage", "Northwood Wholesale", "15.50", "6.90", 58, 15),
        ]
        for sku, name, cat, sup, unit, cost, stock, threshold in catalog:
            products[sku] = product_service.create_product(
                ProductCreate(
                    sku=sku,
                    name=name,
                    description=None,
                    category_id=categories[cat].id,
                    supplier_id=suppliers[sup].id,
                    unit_price=M(unit),
                    cost_price=M(cost),
                    stock_quantity=stock,
                    low_stock_threshold=threshold,
                    is_active=True,
                )
            )

        # ---- orders (fictional) -------------------------------------------
        order_service = OrderService(db)

        def make_order(customer_idx: int, lines: list[tuple[str, int]]) -> Order:
            return order_service.create_order(
                OrderCreate(
                    customer_id=customers[customer_idx % len(customers)].id,
                    items=[
                        OrderItemCreate(product_id=products[sku].id, quantity=qty)
                        for sku, qty in lines
                    ],
                )
            )

        drafts = [
            make_order(0, [("LMP-1001", 2), ("STA-3002", 3)]),
            make_order(1, [("FUR-2001", 1)]),
            make_order(2, [("KIT-4001", 4), ("STA-3001", 5)]),
            make_order(3, [("STO-5001", 6), ("STA-3003", 2)]),
            make_order(4, [("LMP-1002", 1), ("LMP-1003", 1)]),
        ]

        def to_confirm(lines: list[tuple[str, int]], customer_idx: int) -> Order:
            return make_order(customer_idx, lines)

        confirmed = [
            to_confirm([("LMP-1001", 1), ("STA-3001", 4)], 5),
            to_confirm([("KIT-4002", 2)], 6),
            to_confirm([("FUR-2002", 1), ("STA-3002", 2)], 7),
            to_confirm([("STO-5001", 3)], 0),
            to_confirm([("LMP-1001", 3)], 1),
        ]
        completed = [
            to_confirm([("STA-3001", 10), ("STA-3002", 5)], 2),
            to_confirm([("KIT-4001", 2)], 3),
        ]
        cancelled_confirmed = to_confirm([("LMP-1003", 1), ("KIT-4002", 2)], 4)
        cancelled_draft = make_order(5, [("FUR-2003", 1)])

        for order in confirmed:
            order_service.confirm_order(order.id)
        for order in completed:
            order_service.confirm_order(order.id)
            order_service.complete_order(order.id)
        order_service.confirm_order(cancelled_confirmed.id)
        order_service.cancel_order(cancelled_confirmed.id)
        order_service.cancel_order(cancelled_draft.id)

        all_orders = drafts + confirmed + completed + [cancelled_confirmed, cancelled_draft]

        # Backdate orders + their movements so the dashboard looks like real
        # history. Movements referenced by the order get the same timestamp.
        now = utcnow()
        for index, order in enumerate(all_orders):
            days_ago = len(all_orders) - index
            when = now - timedelta(days=days_ago, hours=index % 5)
            order.created_at = when
            order.updated_at = when
            for movement in (
                db.query(StockMovement)
                .filter(StockMovement.reference_type == "order", StockMovement.reference_id == order.id)
                .all()
            ):
                movement.created_at = when

        db.commit()

        counts = {
            "products": db.query(Product).count(),
            "low_stock": sum(1 for p in db.query(Product).all() if p.is_low_stock),
            "orders": db.query(Order).count(),
            "confirmed": db.query(Order).filter(Order.status == OrderStatus.CONFIRMED).count(),
            "completed": db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count(),
            "cancelled": db.query(Order).filter(Order.status == OrderStatus.CANCELLED).count(),
            "draft": db.query(Order).filter(Order.status == OrderStatus.DRAFT).count(),
            "movements": db.query(StockMovement).count(),
        }
        print("Seed complete (all data is fictional):")
        for key, value in counts.items():
            print(f"  {key:>10}: {value}")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ShopStock demo data (fictional).")
    parser.add_argument("--reset", action="store_true", help="delete the SQLite database file first")
    args = parser.parse_args()
    if args.reset:
        _reset_sqlite_file()
    seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
