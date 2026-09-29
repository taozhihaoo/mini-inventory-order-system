"""Category API tests: CRUD, duplicate names, in-use delete protection."""

from __future__ import annotations


def test_create_category_returns_201(api):
    body = api.create_category("Books", description="Printed media")
    assert body["id"] > 0
    assert body["name"] == "Books"
    assert body["description"] == "Printed media"
    assert body["product_count"] == 0
    assert body["created_at"]


def test_create_duplicate_category_name_conflicts(api, error_shape):
    api.create_category("Duplicate Cat")
    response = api.client.post("/categories", json={"name": "Duplicate Cat"})
    assert response.status_code == 409
    assert error_shape(response)["code"] == "duplicate"


def test_create_duplicate_name_is_case_insensitive(api):
    api.create_category("Stationery")
    response = api.client.post("/categories", json={"name": "stationery"})
    assert response.status_code == 409


def test_create_category_without_name_fails(client, error_shape):
    response = client.post("/categories", json={"description": "no name"})
    assert response.status_code == 422
    error_shape(response)


def test_create_category_name_too_long_fails(client):
    response = client.post("/categories", json={"name": "x" * 101})
    assert response.status_code == 422


def test_list_categories_contains_created(api):
    api.create_category("Listed Cat")
    response = api.client.get("/categories")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert "Listed Cat" in names


def test_search_categories(api):
    api.create_category("Electronics")
    api.create_category("Toys")
    body = api.client.get("/categories", params={"search": "elec"}).json()
    assert [item["name"] for item in body["items"]] == ["Electronics"]


def test_get_category_and_missing(api, error_shape):
    created = api.create_category("Fetch Me")
    found = api.client.get(f"/categories/{created['id']}")
    assert found.status_code == 200
    assert found.json()["name"] == "Fetch Me"

    missing = api.client.get("/categories/9999")
    assert missing.status_code == 404
    assert error_shape(missing)["code"] == "not_found"


def test_update_category(api):
    created = api.create_category("Old Name")
    response = api.client.put(
        f"/categories/{created['id']}", json={"name": "New Name", "description": "updated"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "updated"


def test_update_category_to_duplicate_conflicts(api):
    api.create_category("First")
    other = api.create_category("Second")
    response = api.client.put(f"/categories/{other['id']}", json={"name": "First"})
    assert response.status_code == 409


def test_delete_unused_category(api):
    created = api.create_category("Doomed")
    response = api.client.delete(f"/categories/{created['id']}")
    assert response.status_code == 204
    assert api.client.get(f"/categories/{created['id']}").status_code == 404


def test_delete_in_use_category_blocked(api, error_shape):
    category = api.create_category("In Use")
    api.create_product(category_id=category["id"])
    response = api.client.delete(f"/categories/{category['id']}")
    assert response.status_code == 409
    assert error_shape(response)["code"] == "referenced_by_other_records"
    assert "In Use" in error_shape(response)["message"]


def test_product_count_in_list(api):
    category = api.create_category("Counted")
    api.create_product(category_id=category["id"])
    api.create_product(category_id=category["id"])
    body = api.client.get("/categories", params={"search": "Counted"}).json()
    assert body["items"][0]["product_count"] == 2
