"""Smoke tests for the health endpoint and OpenAPI schema."""

from __future__ import annotations


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "ShopStock" in body["app"]


def test_openapi_schema_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for endpoint in [
        "/health",
        "/categories",
        "/suppliers",
        "/customers",
        "/products",
        "/products/export.csv",
        "/products/import",
        "/inventory/low-stock",
        "/inventory/movements",
        "/orders",
        "/dashboard/summary",
    ]:
        assert endpoint in paths, f"missing endpoint {endpoint}"
