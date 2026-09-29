"""Dashboard aggregation tests."""

from __future__ import annotations


def test_empty_dashboard_is_all_zeros(api):
    body = api.client.get("/dashboard/summary").json()
    assert body["total_products"] == 0
    assert body["active_products"] == 0
    assert body["low_stock_products"] == 0
    assert body["inventory_value"] == 0
    assert body["total_orders"] == 0
    assert body["confirmed_orders"] == 0
    assert body["completed_orders"] == 0
    assert body["sales_amount"] == 0
    assert body["recent_orders"] == []
    assert body["low_stock_list"] == []
    assert body["recent_movements"] == []


def test_product_counts_and_low_stock(api):
    api.create_product(stock_quantity=50, low_stock_threshold=5)
    api.create_product(stock_quantity=2, low_stock_threshold=5)
    inactive = api.create_product(stock_quantity=0, low_stock_threshold=1)
    api.client.put(f"/products/{inactive['id']}", json={"is_active": False})

    body = api.client.get("/dashboard/summary").json()
    assert body["total_products"] == 3
    assert body["active_products"] == 2
    assert body["low_stock_products"] == 1
    assert len(body["low_stock_list"]) == 1
    assert body["low_stock_list"][0]["stock_quantity"] == 2


def test_inventory_value_uses_cost_price(api):
    api.create_product(stock_quantity=10, cost_price="2.50")  # 25.00
    api.create_product(stock_quantity=3, cost_price="10.00")  # 30.00
    api.create_product(stock_quantity=1, cost_price=None)  # no cost -> not counted
    body = api.client.get("/dashboard/summary").json()
    assert body["inventory_value"] == 55.0


def test_order_counts_and_sales_amount(api):
    customer = api.create_customer()
    product = api.create_product(stock_quantity=100, cost_price="5.00", unit_price="10.00")
    draft = api.create_order(customer["id"], [(product["id"], 1)]).json()  # 10.00
    confirmed = api.create_order(customer["id"], [(product["id"], 2)]).json()  # 20.00
    api.confirm_order(confirmed["id"])
    completed = api.create_order(customer["id"], [(product["id"], 3)]).json()  # 30.00
    api.confirm_order(completed["id"])
    api.complete_order(completed["id"])

    body = api.client.get("/dashboard/summary").json()
    assert body["total_orders"] == 3
    assert body["confirmed_orders"] == 1
    assert body["completed_orders"] == 1
    assert body["sales_amount"] == 50.0  # confirmed + completed only
    assert len(body["recent_orders"]) == 3


def test_recent_orders_are_newest_first_and_capped(api):
    customer = api.create_customer()
    product = api.create_product(stock_quantity=100)
    for _ in range(12):
        api.create_order(customer["id"], [(product["id"], 1)])
    body = api.client.get("/dashboard/summary").json()
    assert len(body["recent_orders"]) == 8
    dates = [o["created_at"] for o in body["recent_orders"]]
    assert dates == sorted(dates, reverse=True)


def test_recent_movements_populated(api):
    product = api.create_product()
    for _ in range(3):
        api.stock_in(product["id"], 1)
    body = api.client.get("/dashboard/summary").json()
    assert len(body["recent_movements"]) == 3
    assert body["recent_movements"][0]["product"]["sku"] == product["sku"]
    assert body["recent_movements"][0]["stock_after"] == 3
