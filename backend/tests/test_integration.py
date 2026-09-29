"""End-to-end integration tests: HTTP -> FastAPI -> Service -> SQLAlchemy -> SQLite.

No mock database anywhere; every test drives the real application stack over HTTP.
"""

from __future__ import annotations

import io


def test_full_inventory_lifecycle_over_http(api):
    category = api.create_category("Integration Cat")
    supplier = api.create_supplier("Integration Supplier")
    product = api.create_product(
        name="Lifecycle Widget",
        category_id=category["id"],
        supplier_id=supplier["id"],
        stock_quantity=5,
        low_stock_threshold=2,
    )

    api.stock_in(product["id"], 10, note="replenishment")
    api.stock_out(product["id"], 4, note="shrinkage correction")
    api.stock_adjust(product["id"], 9, note="cycle count")

    fetched = api.client.get(f"/products/{product['id']}").json()
    assert fetched["stock_quantity"] == 9
    assert fetched["category"]["name"] == "Integration Cat"
    assert fetched["supplier"]["name"] == "Integration Supplier"

    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    assert [m["movement_type"] for m in movements] == ["ADJUSTMENT", "OUT", "IN", "IN"]
    assert [m["stock_after"] for m in movements] == [9, 11, 15, 5]

    export = api.client.get("/inventory/movements/export.csv")
    assert product["sku"] in export.text


def test_order_lifecycle_create_confirm_cancel_restores_stock(api):
    customer = api.create_customer("Lifecycle Customer")
    product = api.create_product(stock_quantity=10)

    order = api.create_order(customer["id"], [(product["id"], 4)]).json()
    assert order["status"] == "draft"
    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 10

    assert api.confirm_order(order["id"]).status_code == 200
    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 6

    assert api.cancel_order(order["id"]).status_code == 200
    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 10

    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    # newest first: cancel-restoring IN, confirm OUT, then the initial stock IN
    assert [m["movement_type"] for m in movements] == ["IN", "OUT", "IN"]
    assert movements[0]["note"].startswith("Order ORD-")
    assert movements[1]["note"].startswith("Order ORD-")

    # A cancelled order cannot be completed.
    assert api.complete_order(order["id"]).status_code == 409


def test_complete_flow_and_dashboard_reflect_reality(api):
    customer = api.create_customer()
    product = api.create_product(stock_quantity=30, cost_price="4.00")

    order = api.create_order(customer["id"], [(product["id"], 5)]).json()
    api.confirm_order(order["id"])
    api.complete_order(order["id"])

    summary = api.client.get("/dashboard/summary").json()
    assert summary["total_products"] == 1
    assert summary["total_orders"] == 1
    assert summary["completed_orders"] == 1
    assert summary["sales_amount"] == order["total_amount"]
    assert summary["inventory_value"] == 25 * 4  # 25 remaining * 4.00 cost
    assert summary["recent_orders"][0]["order_number"] == order["order_number"]


def test_low_stock_surface_after_sales(api):
    customer = api.create_customer()
    product = api.create_product(stock_quantity=6, low_stock_threshold=4)
    order = api.create_order(customer["id"], [(product["id"], 3)]).json()
    api.confirm_order(order["id"])

    low = api.client.get("/inventory/low-stock").json()
    assert [p["id"] for p in low] == [product["id"]]
    products = api.client.get("/products", params={"low_stock": "true"}).json()
    assert products["total"] == 1


def test_csv_round_trip_export_then_reimport(api):
    api.create_category("RoundTrip")
    api.create_product(sku="RT-001", name="Round Trip Item", stock_quantity=5)
    export = api.client.get("/products/export.csv")

    response = api.client.post(
        "/products/import",
        files={"file": ("products.csv", io.BytesIO(export.content), "text/csv")},
    )
    body = response.json()
    assert body["imported"] == 0  # same SKU already exists
    assert body["skipped"] == 1
    assert any("already exists" in e["message"] for e in body["errors"])


def test_error_shape_is_uniform(api):
    missing = api.client.get("/products/123456")
    assert missing.status_code == 404
    assert set(missing.json()["error"].keys()) == {"code", "message"}

    invalid = api.client.post("/products", json={"sku": "!!!", "name": "", "unit_price": "-1"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    conflict = api.client.post(
        "/products", json={"sku": "SHAPE-1", "name": "First", "unit_price": "1"}
    )
    assert conflict.status_code == 201
    duplicate = api.client.post(
        "/products", json={"sku": "SHAPE-1", "name": "Second", "unit_price": "1"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate"


def test_pagination_contract_is_uniform(api):
    for _ in range(3):
        api.create_product()
    body = api.client.get("/products", params={"page": 2, "page_size": 2}).json()
    assert set(body.keys()) == {"items", "total", "page", "page_size", "total_pages"}
    assert body == {
        "items": body["items"],
        "total": 3,
        "page": 2,
        "page_size": 2,
        "total_pages": 2,
    }
    assert len(body["items"]) == 1
