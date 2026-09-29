"""Supplier API tests."""

from __future__ import annotations


def test_create_supplier(api):
    body = api.create_supplier("Acme Supplies", email="sales@acme.example.com", phone="555-0001")
    assert body["id"] > 0
    assert body["name"] == "Acme Supplies"
    assert body["email"] == "sales@acme.example.com"
    assert body["product_count"] == 0


def test_create_supplier_invalid_email(client, error_shape):
    response = client.post("/suppliers", json={"name": "Bad Email", "email": "not-an-email"})
    assert response.status_code == 422
    error_shape(response)


def test_create_supplier_missing_name(client):
    response = client.post("/suppliers", json={"email": "x@example.com"})
    assert response.status_code == 422


def test_list_and_search_suppliers(api):
    api.create_supplier("Global Parts")
    api.create_supplier("Local Woodworks")
    body = api.client.get("/suppliers", params={"search": "local"}).json()
    assert [item["name"] for item in body["items"]] == ["Local Woodworks"]


def test_get_supplier_missing(api, error_shape):
    response = api.client.get("/suppliers/4242")
    assert response.status_code == 404
    assert error_shape(response)["code"] == "not_found"


def test_update_supplier(api):
    created = api.create_supplier("Old Supplier")
    response = api.client.put(f"/suppliers/{created['id']}", json={"phone": "555-9999"})
    assert response.status_code == 200
    assert response.json()["phone"] == "555-9999"
    assert response.json()["name"] == "Old Supplier"


def test_delete_unused_supplier(api):
    created = api.create_supplier("Disposable Supplier")
    assert api.client.delete(f"/suppliers/{created['id']}").status_code == 204
    assert api.client.get(f"/suppliers/{created['id']}").status_code == 404


def test_delete_supplier_in_use_blocked(api, error_shape):
    supplier = api.create_supplier("Sticky Supplier")
    api.create_product(supplier_id=supplier["id"])
    response = api.client.delete(f"/suppliers/{supplier['id']}")
    assert response.status_code == 409
    assert error_shape(response)["code"] == "referenced_by_other_records"


def test_supplier_product_count(api):
    supplier = api.create_supplier("Counted Supplier")
    api.create_product(supplier_id=supplier["id"])
    body = api.client.get("/suppliers", params={"search": "Counted"}).json()
    assert body["items"][0]["product_count"] == 1
