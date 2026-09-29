"""Order tests: lifecycle state machine, totals, transactional stock effects."""

from __future__ import annotations

import re
from datetime import datetime


def _order_body(api, *, stock=10, qty=3):
    customer = api.create_customer()
    product = api.create_product(stock_quantity=stock)
    response = api.create_order(customer["id"], [(product["id"], qty)])
    assert response.status_code == 201, response.text
    return response.json(), customer, product


def test_create_draft_order(api):
    order, _, _ = _order_body(api, stock=10, qty=3)
    assert order["status"] == "draft"
    assert re.fullmatch(r"ORD-\d{8}-\d{4}", order["order_number"])
    assert len(order["items"]) == 1
    item = order["items"][0]
    assert item["quantity"] == 3
    assert item["unit_price"] == 19.9  # snapshot of product price
    assert item["line_total"] == 59.7
    assert order["total_amount"] == 59.7


def test_order_numbers_increment_same_day(api):
    o1, _, _ = _order_body(api)
    o2, _, _ = _order_body(api)
    assert o2["order_number"] != o1["order_number"]
    assert int(o2["order_number"].rsplit("-", 1)[1]) == int(o1["order_number"].rsplit("-", 1)[1]) + 1


def test_create_order_unknown_customer(api, error_shape):
    product = api.create_product()
    response = api.create_order(555555, [(product["id"], 1)])
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_create_order_unknown_product(api):
    customer = api.create_customer()
    response = api.create_order(customer["id"], [(888888, 1)])
    assert response.status_code == 404


def test_create_order_zero_quantity_rejected(api):
    customer = api.create_customer()
    product = api.create_product()
    response = api.create_order(customer["id"], [(product["id"], 0)])
    assert response.status_code == 422


def test_create_order_empty_items_rejected(api):
    customer = api.create_customer()
    response = api.create_order(customer["id"], [])
    assert response.status_code == 422


def test_create_order_inactive_product_rejected(api):
    customer = api.create_customer()
    product = api.create_product()
    api.client.put(f"/products/{product['id']}", json={"is_active": False})
    response = api.create_order(customer["id"], [(product["id"], 1)])
    assert response.status_code == 422
    assert "inactive" in response.json()["error"]["message"]


def test_duplicate_product_lines_are_merged(api):
    customer = api.create_customer()
    product = api.create_product(stock_quantity=100)
    order = api.create_order(customer["id"], [(product["id"], 1), (product["id"], 2)]).json()
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 3


def test_confirm_order_deducts_stock_and_writes_movements(api):
    order, customer, product = _order_body(api, stock=10, qty=4)
    created_at_before = api.client.get(f"/products/{product['id']}").json()["stock_quantity"]
    assert created_at_before == 10

    response = api.confirm_order(order["id"])
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    fetched = api.client.get(f"/orders/{order['id']}").json()
    assert fetched["status"] == "confirmed"

    after = api.client.get(f"/products/{product['id']}").json()
    assert after["stock_quantity"] == 6

    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    outs = [m for m in movements if m["movement_type"] == "OUT"]
    assert len(outs) == 1
    assert outs[0]["quantity"] == 4
    assert outs[0]["stock_after"] == 6
    assert outs[0]["reference_type"] == "order"
    assert outs[0]["reference_id"] == order["id"]
    assert order["order_number"] in outs[0]["note"]
    assert customer["name"]


def test_confirm_order_twice_rejected(api, error_shape):
    order, _, _ = _order_body(api)
    assert api.confirm_order(order["id"]).status_code == 200
    response = api.confirm_order(order["id"])
    assert response.status_code == 409
    assert error_shape(response)["code"] == "invalid_state_transition"


def test_confirm_with_insufficient_stock_rolls_back_everything(api):
    """Two-line order where the second product lacks stock: no partial effects."""
    customer = api.create_customer()
    p1 = api.create_product(stock_quantity=100)
    p2 = api.create_product(stock_quantity=1)
    order = api.create_order(customer["id"], [(p1["id"], 5), (p2["id"], 3)]).json()

    response = api.confirm_order(order["id"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"

    # Full rollback: statuses, stock and movements are all untouched.
    assert api.client.get(f"/orders/{order['id']}").json()["status"] == "draft"
    assert api.client.get(f"/products/{p1['id']}").json()["stock_quantity"] == 100
    assert api.client.get(f"/products/{p2['id']}").json()["stock_quantity"] == 1
    for product in (p1, p2):
        movements = api.client.get(f"/products/{product['id']}/stock/movements").json()
        assert movements["total"] == 1  # only the initial stock IN remains


def test_cancel_draft_order_does_not_touch_stock(api):
    order, _, product = _order_body(api, stock=7, qty=2)
    response = api.cancel_order(order["id"])
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 7
    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()
    assert movements["total"] == 1  # only the initial stock IN


def test_cancel_confirmed_order_restores_stock(api):
    order, _, product = _order_body(api, stock=10, qty=4)
    api.confirm_order(order["id"])
    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 6

    response = api.cancel_order(order["id"])
    assert response.status_code == 200
    assert response.json()["previous_status"] == "confirmed"

    assert api.client.get(f"/products/{product['id']}").json()["stock_quantity"] == 10
    movements = api.client.get(f"/products/{product['id']}/stock/movements").json()["items"]
    # newest first: cancel-restoring IN, confirm OUT, then the initial stock IN (qty 10)
    assert [m["movement_type"] for m in movements] == ["IN", "OUT", "IN"]
    restore, out, initial = movements
    assert restore["quantity"] == 4
    assert restore["stock_after"] == 10
    assert restore["reference_type"] == "order"
    assert out["quantity"] == 4
    assert out["stock_after"] == 6
    assert initial["quantity"] == 10


def test_cancel_completed_order_rejected(api, error_shape):
    order, _, _ = _order_body(api)
    api.confirm_order(order["id"])
    api.complete_order(order["id"])
    response = api.cancel_order(order["id"])
    assert response.status_code == 409
    assert error_shape(response)["code"] == "invalid_state_transition"


def test_cancel_twice_rejected(api, error_shape):
    order, _, _ = _order_body(api)
    api.cancel_order(order["id"])
    response = api.cancel_order(order["id"])
    assert response.status_code == 409


def test_complete_confirmed_order(api):
    order, _, _ = _order_body(api)
    assert api.confirm_order(order["id"]).status_code == 200
    response = api.complete_order(order["id"])
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert api.client.get(f"/orders/{order['id']}").json()["status"] == "completed"


def test_complete_draft_order_rejected(api, error_shape):
    order, _, _ = _order_body(api)
    response = api.complete_order(order["id"])
    assert response.status_code == 409
    assert error_shape(response)["code"] == "invalid_state_transition"


def test_complete_cancelled_order_rejected(api):
    order, _, _ = _order_body(api)
    api.confirm_order(order["id"])
    api.cancel_order(order["id"])
    assert api.complete_order(order["id"]).status_code == 409


def test_get_order_includes_items_and_customer(api):
    order, customer, product = _order_body(api)
    body = api.client.get(f"/orders/{order['id']}").json()
    assert body["customer"]["id"] == customer["id"]
    assert body["customer"]["name"] == customer["name"]
    assert body["items"][0]["product"]["sku"] == product["sku"]
    assert body["items"][0]["product"]["name"] == product["name"]
    assert body["created_at"]
    datetime.fromisoformat(body["created_at"])


def test_get_order_missing(api, error_shape):
    response = api.client.get("/orders/909090")
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_order_list_pagination_and_item_count(api):
    for _ in range(3):
        _order_body(api, qty=2)
    body = api.client.get("/orders", params={"page_size": 2}).json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert all(item["item_count"] == 2 for item in body["items"])


def test_order_list_filters(api):
    order, customer, product = _order_body(api)
    api.confirm_order(order["id"])
    other_customer = api.create_customer()
    draft = api.create_order(other_customer["id"], [(product["id"], 1)]).json()

    confirmed = api.client.get("/orders", params={"status": "confirmed"}).json()
    assert [o["id"] for o in confirmed["items"]] == [order["id"]]

    by_customer = api.client.get("/orders", params={"customer_id": other_customer["id"]}).json()
    assert [o["id"] for o in by_customer["items"]] == [draft["id"]]

    by_number = api.client.get("/orders", params={"search": order["order_number"]}).json()
    assert [o["id"] for o in by_number["items"]] == [order["id"]]

    invalid = api.client.get("/orders", params={"status": "bogus"})
    assert invalid.status_code == 422


def test_order_date_range_filter(api):
    order, _, _ = _order_body(api)
    body = api.client.get(
        "/orders",
        params={"date_from": "2000-01-01", "date_to": "2100-01-01"},
    ).json()
    assert body["total"] == 1
    empty = api.client.get(
        "/orders",
        params={"date_from": "2000-01-01", "date_to": "2001-01-01"},
    ).json()
    assert empty["total"] == 0
