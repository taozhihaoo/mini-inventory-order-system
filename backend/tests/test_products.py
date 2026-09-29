"""Product API tests: CRUD, validation, duplicate SKU, listing features."""

from __future__ import annotations

import re


def test_create_product_defaults(api):
    body = api.create_product(name="Basic Widget")
    assert body["sku"].startswith("SKU-")
    assert body["stock_quantity"] == 0
    assert body["is_active"] is True
    assert body["category"] is None
    assert body["supplier"] is None


def test_create_product_with_initial_stock_creates_movement(api):
    body = api.create_product(stock_quantity=7)
    assert body["stock_quantity"] == 7
    movements = api.client.get(f"/products/{body['id']}/stock/movements").json()["items"]
    assert len(movements) == 1
    assert movements[0]["movement_type"] == "IN"
    assert movements[0]["quantity"] == 7
    assert movements[0]["stock_after"] == 7


def test_create_product_low_stock_flag(api):
    low = api.create_product(stock_quantity=2, low_stock_threshold=5)
    assert low["is_low_stock"] is True
    healthy = api.create_product(stock_quantity=10, low_stock_threshold=5)
    assert healthy["is_low_stock"] is False
    zero_zero = api.create_product(stock_quantity=0, low_stock_threshold=0)
    assert zero_zero["is_low_stock"] is True  # 0 <= 0 counts as low


def test_create_product_duplicate_sku_conflicts(api, error_shape):
    api.create_product(sku="DUP-001")
    response = api.client.post(
        "/products", json={"sku": "DUP-001", "name": "Second", "unit_price": "1.00"}
    )
    assert response.status_code == 409
    assert error_shape(response)["code"] == "duplicate"


def test_create_product_duplicate_sku_case_insensitive(api):
    api.create_product(sku="CASE-001")
    response = api.client.post(
        "/products", json={"sku": "case-001", "name": "Other", "unit_price": "1.00"}
    )
    assert response.status_code == 409


def test_create_product_missing_name_fails(client):
    response = client.post("/products", json={"sku": "X-1", "unit_price": "1.00"})
    assert response.status_code == 422


def test_create_product_negative_price_fails(client):
    response = client.post(
        "/products", json={"sku": "NEG-1", "name": "Bad", "unit_price": "-5.00"}
    )
    assert response.status_code == 422


def test_create_product_invalid_sku_pattern_fails(client):
    response = client.post(
        "/products", json={"sku": "bad sku!", "name": "Bad", "unit_price": "1.00"}
    )
    assert response.status_code == 422


def test_create_product_unknown_category(api, error_shape):
    response = api.client.post(
        "/products",
        json={"sku": "GHOST-1", "name": "Ghost", "unit_price": "1.00", "category_id": 999},
    )
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_create_product_unknown_supplier(api):
    response = api.client.post(
        "/products",
        json={"sku": "GHOST-2", "name": "Ghost", "unit_price": "1.00", "supplier_id": 999},
    )
    assert response.status_code == 404


def test_get_product_missing(api, error_shape):
    response = api.client.get("/products/31337")
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_update_product_fields(api):
    created = api.create_product(name="Old", unit_price="10.00")
    response = api.client.put(
        f"/products/{created['id']}",
        json={"name": "New", "unit_price": "12.50", "description": "updated"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New"
    assert response.json()["unit_price"] == 12.5
    assert response.json()["description"] == "updated"


def test_update_product_sku_conflict(api):
    api.create_product(sku="TAKEN-1")
    other = api.create_product(sku="MINE-1")
    response = api.client.put(f"/products/{other['id']}", json={"sku": "TAKEN-1"})
    assert response.status_code == 409


def test_update_product_cannot_change_stock_directly(api):
    """Stock may only change through inventory endpoints."""
    created = api.create_product(stock_quantity=5)
    response = api.client.put(f"/products/{created['id']}", json={"stock_quantity": 999})
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == 5


def test_deactivate_product_via_update(api):
    created = api.create_product()
    response = api.client.put(f"/products/{created['id']}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_list_pagination(api):
    for _ in range(25):
        api.create_product()
    first = api.client.get("/products", params={"page": 1, "page_size": 20}).json()
    assert first["total"] == 25
    assert len(first["items"]) == 20
    assert first["page"] == 1
    assert first["total_pages"] == 2
    second = api.client.get("/products", params={"page": 2, "page_size": 20}).json()
    assert len(second["items"]) == 5


def test_list_page_size_capped(client):
    response = client.get("/products", params={"page_size": 5000})
    assert response.status_code == 422


def test_list_search_by_name_and_sku(api):
    api.create_product(sku="FIND-001", name="Searching Widget")
    api.create_product(sku="OTHER-1", name="Different Thing")
    by_name = api.client.get("/products", params={"search": "searching"}).json()
    assert [p["sku"] for p in by_name["items"]] == ["FIND-001"]
    by_sku = api.client.get("/products", params={"search": "OTHER"}).json()
    assert [p["sku"] for p in by_sku["items"]] == ["OTHER-1"]


def test_list_filters(api):
    category = api.create_category("Filtered Cat")
    other_category = api.create_category("Other Cat")
    supplier = api.create_supplier("Filtered Supplier")
    api.create_product(category_id=category["id"], supplier_id=supplier["id"], stock_quantity=1,
                       low_stock_threshold=3)
    api.create_product(category_id=other_category["id"], stock_quantity=10)

    by_category = api.client.get("/products", params={"category_id": category["id"]}).json()
    assert by_category["total"] == 1
    by_supplier = api.client.get("/products", params={"supplier_id": supplier["id"]}).json()
    assert by_supplier["total"] == 1


def test_list_filter_active_and_low_stock(api):
    active_low = api.create_product(stock_quantity=1, low_stock_threshold=5)
    inactive = api.create_product(stock_quantity=50)
    api.client.put(f"/products/{inactive['id']}", json={"is_active": False})

    only_active = api.client.get("/products", params={"is_active": "true"}).json()
    assert only_active["total"] == 1
    assert only_active["items"][0]["id"] == active_low["id"]

    low = api.client.get("/products", params={"low_stock": "true"}).json()
    assert low["total"] == 1
    assert low["items"][0]["id"] == active_low["id"]

    not_low = api.client.get("/products", params={"low_stock": "false"}).json()
    assert not_low["total"] == 1
    assert not_low["items"][0]["id"] == inactive["id"]


def test_list_sorting(api):
    api.create_product(name="A Item", unit_price="30.00")
    api.create_product(name="B Item", unit_price="10.00")
    body = api.client.get("/products", params={"sort_by": "unit_price", "sort_dir": "asc"}).json()
    prices = [p["unit_price"] for p in body["items"]]
    assert prices == sorted(prices)


def test_delete_unreferenced_product(api):
    created = api.create_product()
    assert api.client.delete(f"/products/{created['id']}").status_code == 204
    assert api.client.get(f"/products/{created['id']}").status_code == 404


def test_delete_product_with_movements_blocked(api, error_shape):
    created = api.create_product(stock_quantity=5)
    response = api.client.delete(f"/products/{created['id']}")
    assert response.status_code == 409
    assert error_shape(response)["code"] == "referenced_by_other_records"
    assert "Deactivate" in error_shape(response)["message"]


def test_product_order_number_format_on_order(api):
    """Order numbers are server-generated and follow ORD-YYYYMMDD-NNNN."""
    customer = api.create_customer()
    product = api.create_product(stock_quantity=5)
    order = api.create_order(customer["id"], [(product["id"], 1)]).json()
    assert re.fullmatch(r"ORD-\d{8}-\d{4}", order["order_number"])
