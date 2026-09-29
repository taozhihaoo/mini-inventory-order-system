# ShopStock — Design Document

Small Business Inventory & Order Management System (independent portfolio project).

This document is the design produced **before** implementation. Scope is intentionally
kept small-but-complete: one backend service, one frontend app, one SQLite database.

## A. Page Structure

Sidebar layout (business-software style, custom CSS, no heavy UI framework):

```
Sidebar              Main area (header + page content)
├── Dashboard        /                stat cards, recent orders, low stock, recent movements
├── Products         /products        search, category/supplier/active/low-stock filters,
│                    /products/:id    detail: info, stock, movements, recent orders, stock ops
├── Inventory        /inventory       tabs: Stock Operations | Movements | Low Stock
├── Orders           /orders          filters (status, customer, date range, number search)
│                    /orders/new      create draft order (multi-line item editor)
│                    /orders/:id      detail + Confirm / Cancel / Complete actions
├── Customers        /customers       list, search, pagination, CRUD
├── Suppliers        /suppliers       list, search, pagination, CRUD
└── Categories       /categories      list, CRUD, in-use delete protection
```

Every list page implements: loading / empty / error states, success feedback (toasts),
form validation, and destructive-action confirmation dialogs.

## B. Backend Module Structure

```
backend/app/
├── main.py            FastAPI app factory, CORS, exception handlers, lifespan init
├── config.py          Settings from environment (DATABASE_URL, CORS_ORIGINS, APP_ENV)
├── database.py        engine/session factory, FK+busy_timeout pragmas, get_db dependency
├── models/            SQLAlchemy 2.x ORM models (one file per entity)
├── schemas/           Pydantic v2 request/response models (+ generic Page[T])
├── repositories/      query layer only (filters, pagination, sorting, aggregates)
├── services/          ALL business rules: inventory, orders, CSV, dashboard
├── api/               thin route handlers (no business logic)
├── utils/             csv sanitization, UTC clock helper
└── seed.py            `python -m app.seed [--reset]` demo data CLI
```

Call direction is strictly `API → Service → Repository → DB`. Stock deduction, order
confirmation and totals calculation live in services, never in route functions.

## C. Database Entities

- **Category**: id, name (unique), description, created_at
- **Supplier**: id, name, email, phone, notes, created_at, updated_at
- **Customer**: id, name, email, phone, notes, created_at, updated_at
- **Product**: id, sku (unique), name, description, category_id?, supplier_id?,
  unit_price, cost_price?, stock_quantity (≥0), low_stock_threshold (≥0), is_active,
  created_at, updated_at
- **Order**: id, order_number (unique), customer_id, status
  (draft|confirmed|completed|cancelled), total_amount, created_at, updated_at
- **OrderItem**: id, order_id, product_id, quantity (>0), unit_price (snapshot), line_total
- **StockMovement**: id, product_id, movement_type (IN|OUT|ADJUSTMENT), quantity
  (positive for IN/OUT, signed delta for ADJUSTMENT), stock_after, reference_type?,
  reference_id?, note?, created_at

Indexes: products.sku, products.category_id, products.supplier_id, orders.order_number,
orders.status, orders.customer_id, stock_movements.product_id, stock_movements.created_at.
DB-level CHECK constraints: prices ≥ 0, stock ≥ 0, order item quantity > 0.
Foreign keys are enforced (`PRAGMA foreign_keys=ON`). Timestamps are naive UTC.

## D. Business Rules

Inventory (single choke point `inventory_service.record_movement`, always in a DB
transaction; stock is never mutated directly by routes/frontend):

- Stock In / Stock Out / Stock Adjust endpoints; quantity must be > 0 (adjust targets a
  new absolute quantity ≥ 0, delta ≠ 0).
- Every change writes a StockMovement with the resulting `stock_after`.
- OUT cannot push stock below 0 (409 otherwise). Any failure rolls back the whole
  transaction — no "stock changed but movement missing" half-states.
- Responses include the updated product (new stock quantity).

Orders:

- `POST /orders` creates a **draft** with item lines (product existence/active checked,
  quantity > 0, unit price snapshotted from product).
- `POST /orders/{id}/confirm` (draft → confirmed), in ONE transaction: validate items &
  stock (aggregated per product), compute total, deduct stock atomically, write one
  StockMovement OUT per line, set status. Any failure ⇒ full rollback, no partial
  deduction.
- `POST /orders/{id}/cancel`: draft → cancelled (no stock change); confirmed → cancelled
  restores stock and writes StockMovement IN per line. completed/cancelled ⇒ 409.
- `POST /orders/{id}/complete`: confirmed → completed only.
- Legal transitions: draft→confirmed/cancelled, confirmed→completed/cancelled;
  completed and cancelled are terminal.
- Order numbers `ORD-YYYYMMDD-NNNN` generated server-side, unique (DB constraint,
  generation retries on the unlikely race).

Referential protection: delete is refused (409) for a category/supplier used by
products, a customer with orders, and a product with movements or order items
(deactivate instead).

Low stock: `stock_quantity <= low_stock_threshold` (active products), shown in
Dashboard, product list, and a dedicated low-stock view; `GET /inventory/low-stock`.

CSV: product import validates header exactly, then validates row-by-row (types,
ranges, SKU format, duplicate SKUs within file/DB, category/supplier must exist by
name); bad rows are skipped and reported — good rows still import. Exports for
products, orders (line-level) and stock movements, with CSV-injection sanitization
(cells starting with `= + - @` are prefixed with `'`).

## E. REST API

`GET /health`; FastAPI auto `/docs` + `/openapi.json`. Full CRUD for categories,
suppliers, customers, products (list: page, page_size≤100, search, filters, whitelisted
sorting). Inventory: `POST /products/{id}/stock/in|out|adjust`,
`GET /products/{id}/stock/movements`, `GET /inventory/movements`, `GET /inventory/low-stock`.
Orders: CRUD-lite + `/confirm|/cancel|/complete`, filters. `GET /dashboard/summary`.
CSV: `POST /products/import`, `GET /products/export.csv`, `GET /orders/export.csv`,
`GET /inventory/movements/export.csv`. Extensions beyond the required list:
`GET /inventory/movements`, `GET /products/{id}/orders` (for the product detail page).

Errors are uniform: `{"error": {"code", "message"}}` with correct status codes
(404 not found, 409 conflict/duplicate/state, 422 validation, 500 generic safe message,
no tracebacks leaked).

## F. Frontend State & Pages

React 18 + TypeScript + Vite + react-router. No global state library — per-page
state via a small `useAsync` hook (data/loading/error/refetch) and a `fetch` wrapper
that normalizes API errors. Shared components: Layout (sidebar), Modal,
ConfirmDialog, Toasts, Pagination, StatusBadge, EmptyState, form fields. Custom CSS
(design tokens, tables, badges, forms); responsive with a collapsible sidebar.
Dev server proxies `/api` → `localhost:8000`; production nginx does the same, so the
frontend code is environment-agnostic.

## G. Test Strategy

pytest + FastAPI TestClient against a real in-memory SQLite (StaticPool) — **no mock
database anywhere**. Per-domain suites for CRUD/validation/conflicts, deep suites for
inventory (in/out/adjust/insufficient/rollback/movement integrity) and orders (state
machine, stock deduction/restoration, totals, number generation), CSV suites
(valid/invalid header/bad rows/duplicate SKU/export), dashboard aggregates, and an
end-to-end integration suite: HTTP → FastAPI → Service → SQLAlchemy → SQLite → JSON.
Target: 100+ meaningful tests.

## H. Docker Plan

`docker compose up` starts backend (python:3.11-slim, non-root, healthcheck on
/health, SQLite file on a named volume) and frontend (node build stage → nginx serving
the SPA and proxying `/api` to the backend). Configuration via environment variables
only; no secrets baked into images.

## I. Explicitly Out of Scope

Authentication/authorization/multi-user roles; real payment processing; email
notifications; multi-warehouse; purchase orders (supplier-side); pricing discounts/
taxes; Alembic migrations (create_all init; SQLite single-file app); Kubernetes;
heavy BI charts; Playwright e2e (manual browser smoke verification instead, to keep
scope contained). Single-store, local/business-use application.
