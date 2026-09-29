"""Inventory tests: stock in/out/adjust, movements, rollback guarantees."""

from __future__ import annotations


def test_stock_in_updates_product_and_creates_movement(api):
    product = api.create_product()
    result = api.stock_in(product["id"], 10, note="receiving #1")
    assert result.status_code == 200
    body = result.json()
    assert body == {
        "movement_type": "IN",
        "product_id": product["id"],
        "sku": product["sku"],
        "name": product["name"],
        "previous_quantity": 0,
        "new_quantity": 10,
        "change": 10,
        "movement_id": body["movement_id"],
    }
    fetched = api.client.get(f"/products/{product['id']}").json()
    assert fetched["stock_quantity"] == 10
    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    assert len(movements) == 1
    assert movements[0]["note"] == "receiving #1"
    assert movements[0]["quantity"] == 10
    assert movements[0]["stock_after"] == 10


def test_stock_in_rejects_zero(api, error_shape):
    product = api.create_product()
    response = api.stock_in(product["id"], 0)
    assert response.status_code == 422
    error_shape(response)


def test_stock_in_rejects_negative(api):
    product = api.create_product()
    assert api.stock_in(product["id"], -3).status_code == 422


def test_stock_in_unknown_product(api, error_shape):
    response = api.stock_in(987654, 5)
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_stock_out_updates_stock_and_movement(api):
    product = api.create_product(stock_quantity=8)
    body = api.stock_out(product["id"], 3).json()
    assert body["new_quantity"] == 5
    assert body["change"] == -3
    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    assert movements[0]["movement_type"] == "OUT"
    assert movements[0]["quantity"] == 3  # OUT stores the moved amount, positive
    assert movements[0]["stock_after"] == 5


def test_stock_out_below_zero_rejected(api, error_shape):
    product = api.create_product(stock_quantity=2)
    response = api.stock_out(product["id"], 5)
    assert response.status_code == 409
    assert error_shape(response)["code"] == "insufficient_stock"
    fetched = api.client.get(f"/products/{product['id']}").json()
    assert fetched["stock_quantity"] == 2


def test_stock_out_exact_available_allowed(api):
    product = api.create_product(stock_quantity=4)
    body = api.stock_out(product["id"], 4).json()
    assert body["new_quantity"] == 0
    fetched = api.client.get(f"/products/{product['id']}").json()
    assert fetched["stock_quantity"] == 0
    assert fetched["is_low_stock"] is True


def test_failed_stock_out_writes_no_movement(api):
    """Rollback guarantee: a rejected operation leaves no partial state."""
    product = api.create_product(stock_quantity=1)
    api.stock_out(product["id"], 9)  # rejected
    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()
    # only the initial IN movement from product creation exists
    assert movements["total"] == 1
    assert movements["items"][0]["movement_type"] == "IN"
    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 1


def test_stock_adjust_up_and_down(api):
    product = api.create_product(stock_quantity=10)
    up = api.stock_adjust(product["id"], 15, note="found extra").json()
    assert up["movement_type"] == "ADJUSTMENT"
    assert up["change"] == 5
    down = api.stock_adjust(product["id"], 6).json()
    assert down["change"] == -9
    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    # newest first: two adjustments, then the initial IN from product creation
    assert [m["movement_type"] for m in movements] == ["ADJUSTMENT", "ADJUSTMENT", "IN"]
    assert [m["quantity"] for m in movements[:2]] == [-9, 5]  # signed delta for adjustments
    assert movements[0]["stock_after"] == 6
    assert movements[1]["stock_after"] == 15


def test_stock_adjust_to_same_value_rejected(api, error_shape):
    product = api.create_product(stock_quantity=5)
    response = api.stock_adjust(product["id"], 5)
    assert response.status_code == 422
    error_shape(response)


def test_stock_adjust_negative_target_rejected(api):
    product = api.create_product(stock_quantity=5)
    response = api.client.post(
        f"/products/{product['id']}/stock/adjust", json={"new_quantity": -1}
    )
    assert response.status_code == 422


def test_movements_page_for_product_is_filtered(api):
    other = api.create_product()  # no stock -> no movements
    product = api.create_product(stock_quantity=0)
    api.stock_in(product["id"], 5)
    api.stock_out(product["id"], 2)
    body = api.client.get(f"/products/{product['id']}/stock/movements").json()
    assert body["total"] == 2
    assert all(m["product_id"] == product["id"] for m in body["items"])
    assert api.client.get(f"/products/{other['id']}/stock/movements").json()["total"] == 0


def test_movements_endpoint_filters_by_type(api):
    product = api.create_product()
    api.stock_in(product["id"], 5)
    api.stock_out(product["id"], 1)
    api.stock_adjust(product["id"], 20)

    ins = api.client.get("/inventory/movements", params={"movement_type": "IN"}).json()
    assert ins["total"] == 1
    outs = api.client.get("/inventory/movements", params={"movement_type": "OUT"}).json()
    assert outs["total"] == 1
    adjustments = api.client.get("/inventory/movements", params={"movement_type": "ADJUSTMENT"}).json()
    assert adjustments["total"] == 1


def test_movements_endpoint_rejects_unknown_type(api, error_shape):
    response = api.client.get("/inventory/movements", params={"movement_type": "SIDEWAYS"})
    assert response.status_code == 422
    error_shape(response)


def test_movements_endpoint_filters_by_product(api):
    a = api.create_product()
    b = api.create_product()
    api.stock_in(a["id"], 5)
    api.stock_in(b["id"], 6)
    body = api.client.get("/inventory/movements", params={"product_id": b["id"]}).json()
    assert body["total"] == 1
    assert body["items"][0]["product_id"] == b["id"]
    assert body["items"][0]["product"]["sku"] == b["sku"]


def test_low_stock_endpoint(api):
    healthy = api.create_product(stock_quantity=50, low_stock_threshold=5)
    low = api.create_product(stock_quantity=4, low_stock_threshold=4)
    inactive_low = api.create_product(stock_quantity=0, low_stock_threshold=9)
    api.client.put(f"/products/{inactive_low['id']}", json={"is_active": False})

    body = api.client.get("/inventory/low-stock").json()
    ids = [p["id"] for p in body]
    assert low["id"] in ids
    assert healthy["id"] not in ids
    assert inactive_low["id"] not in ids  # inactive products are not actionable


def test_movement_pagination_contract(api):
    product = api.create_product()
    for _ in range(5):
        api.stock_in(product["id"], 1)
    body = api.client.get(
        f"/products/{product['id']}/stock/movements", params={"page": 1, "page_size": 3}
    ).json()
    assert body["total"] == 5
    assert len(body["items"]) == 3
    assert body["total_pages"] == 2
