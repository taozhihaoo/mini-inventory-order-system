"""Phase 2 hardening regression tests.

Covers the uniform 500 error contract and additional CSV import edge
cases (BOM encoding, whitespace around numbers, excessive precision).
"""

from __future__ import annotations

import io

from app.database import get_db

HEADER = "sku,name,category,supplier,unit_price,cost_price,stock_quantity,low_stock_threshold"


def _csv(*rows: str) -> bytes:
    return ("\n".join([HEADER, *rows]) + "\n").encode("utf-8")


def _import(api, content: bytes):
    return api.client.post(
        "/products/import",
        files={"file": ("products.csv", io.BytesIO(content), "text/csv")},
    )


# ---- error contract ---------------------------------------------------------


def test_unhandled_error_returns_safe_500(client):
    """An unexpected exception must become a generic 500 JSON body — no
    traceback, no internal details leak into the response."""
    from fastapi.testclient import TestClient

    def exploding_db():
        raise RuntimeError("boom: C:\\Users\\someone\\secret.py line 42")

    client.app.dependency_overrides[get_db] = exploding_db
    try:
        safe_client = TestClient(client.app, raise_server_exceptions=False)
        response = safe_client.get("/products")
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "boom" not in response.text
    assert "Traceback" not in response.text
    assert "C:\\" not in response.text


def test_method_not_allowed_is_json(client):
    response = client.patch("/health")
    assert response.status_code == 405


# ---- CSV import robustness --------------------------------------------------


def test_import_accepts_utf8_bom_files(api):
    bom = b"\xef\xbb\xbf"
    content = bom + _csv("BOM-001,BOM Widget,,,12.50,5.00,4,2")
    response = _import(api, content)
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1, body
    assert api.client.get("/products", params={"search": "BOM-001"}).json()["total"] == 1


def test_import_accepts_whitespace_around_numbers(api):
    response = _import(api, _csv("WS-001,Spacey Widget,,, 19.90 , 4.00 , 7 , 2 "))
    body = response.json()
    assert body["imported"] == 1, body
    product = api.client.get("/products", params={"search": "WS-001"}).json()["items"][0]
    assert product["unit_price"] == 19.9
    assert product["stock_quantity"] == 7


def test_import_accepts_integer_price_format(api):
    response = _import(api, _csv("INT-001,Integer Price,,,20,,3,1"))
    body = response.json()
    assert body["imported"] == 1
    product = api.client.get("/products", params={"search": "INT-001"}).json()["items"][0]
    assert product["unit_price"] == 20.0
    assert product["cost_price"] is None


def test_import_rejects_more_than_two_decimal_places(api):
    response = _import(api, _csv("DEC-001,Precision Widget,,,19.999,,1,0"))
    body = response.json()
    assert body["imported"] == 0
    assert body["skipped"] == 1
    assert body["errors"], "row error should be reported"


def test_import_sku_normalized_to_uppercase_on_duplicate_check(api):
    """dsk-001 and DSK-001 must collide regardless of input casing."""
    response = _import(
        api,
        _csv(
            "dsk-001,First,,,10.00,,1,0",
            "DSK-001,Second,,,11.00,,2,0",
        ),
    )
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 1
    # the in-file duplicate check triggers first (case-insensitive via SKU
    # normalization), reporting the collision with the stored row
    assert any(
        "duplicate SKU" in e["message"] and "DSK-001" in e["message"]
        for e in body["errors"]
    ), body["errors"]
    assert api.client.get("/products").json()["total"] == 1


def test_oversized_import_rejected(api, error_shape):
    oversized = b"sku,name,category,supplier,unit_price,cost_price,stock_quantity,low_stock_threshold\n" + b"A-1,Widget,,,1.00,,1,0\n" * 400_000
    if len(oversized) < 5 * 1024 * 1024:
        oversized += b"x" * (5 * 1024 * 1024 - len(oversized) + 1)
    response = _import(api, oversized)
    assert response.status_code == 422
    assert "large" in error_shape(response)["message"].lower()
