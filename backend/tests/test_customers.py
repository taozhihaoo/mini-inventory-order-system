"""Customer API tests."""

from __future__ import annotations


def test_create_customer(api):
    body = api.create_customer("Jane Doe", email="jane@example.com", phone="555-1234")
    assert body["id"] > 0
    assert body["name"] == "Jane Doe"
    assert body["order_count"] == 0


def test_create_customer_invalid_email(client):
    response = client.post("/customers", json={"name": "Bad", "email": "nope"})
    assert response.status_code == 422


def test_create_customer_missing_name(client):
    response = client.post("/customers", json={})
    assert response.status_code == 422


def test_list_and_search_customers(api):
    api.create_customer("Alice Anderson", email="alice@example.com")
    api.create_customer("Bob Brown", email="bob@example.com")
    by_name = api.client.get("/customers", params={"search": "alice"}).json()
    assert [item["name"] for item in by_name["items"]] == ["Alice Anderson"]
    by_email = api.client.get("/customers", params={"search": "bob@"}).json()
    assert [item["name"] for item in by_email["items"]] == ["Bob Brown"]


def test_get_customer_missing(api, error_shape):
    response = api.client.get("/customers/777")
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_update_customer(api):
    created = api.create_customer("Before")
    response = api.client.put(f"/customers/{created['id']}", json={"name": "After", "notes": "vip"})
    assert response.status_code == 200
    assert response.json()["name"] == "After"
    assert response.json()["notes"] == "vip"


def test_delete_unused_customer(api):
    created = api.create_customer("Temporary")
    assert api.client.delete(f"/customers/{created['id']}").status_code == 204
    assert api.client.get(f"/customers/{created['id']}").status_code == 404


def test_delete_customer_with_orders_blocked(api, error_shape):
    customer = api.create_customer("Ordered Once")
    product = api.create_product(stock_quantity=10)
    order = api.create_order(customer["id"], [(product["id"], 1)]).json()
    assert order["id"] > 0
    response = api.client.delete(f"/customers/{customer['id']}")
    assert response.status_code == 409
    assert error_shape(response)["code"] == "referenced_by_other_records"


def test_customer_order_count(api):
    customer = api.create_customer("Two Orders")
    product = api.create_product(stock_quantity=50)
    api.create_order(customer["id"], [(product["id"], 1)])
    api.create_order(customer["id"], [(product["id"], 2)])
    body = api.client.get("/customers", params={"search": "Two Orders"}).json()
    assert body["items"][0]["order_count"] == 2
