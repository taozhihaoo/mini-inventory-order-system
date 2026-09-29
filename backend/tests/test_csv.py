"""CSV import/export tests: header validation, row errors, exports, injection."""

from __future__ import annotations

import io

HEADER = "sku,name,category,supplier,unit_price,cost_price,stock_quantity,low_stock_threshold"


def _csv(*rows: str) -> bytes:
    lines = [HEADER, *rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _import(api, content: bytes):
    response = api.client.post(
        "/products/import",
        files={"file": ("products.csv", io.BytesIO(content), "text/csv")},
    )
    return response


def test_import_valid_rows(api):
    category = api.create_category("Lighting")
    supplier = api.create_supplier("Import Supplier")
    response = _import(
        api,
        _csv(
            "LMP-1,Desk Lamp,Lighting,Import Supplier,39.90,22.50,10,3",
            "LMP-2,Floor Lamp,Lighting,,89.00,,4,1",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {"total_rows": 2, "imported": 2, "skipped": 0, "errors": []}

    products = api.client.get("/products").json()
    assert products["total"] == 2
    lamp = next(p for p in products["items"] if p["sku"] == "LMP-1")
    assert lamp["stock_quantity"] == 10
    assert lamp["category"]["id"] == category["id"]
    assert lamp["supplier"]["id"] == supplier["id"]
    # initial stock recorded as an IN movement
    movements = api.client.get(f"/products/{lamp['id']}/stock/movements").json()
    assert movements["total"] == 1
    assert movements["items"][0]["movement_type"] == "IN"


def test_import_invalid_header_rejected(api, error_shape):
    content = b"sku,product_name\nLMP-1,Lamp\n"
    response = _import(api, content)
    assert response.status_code == 422
    assert "header" in error_shape(response)["message"].lower()


def test_import_empty_file_rejected(api):
    response = _import(api, b"")
    assert response.status_code == 422


def test_import_missing_unit_price_skips_row(api):
    response = _import(api, _csv("LMP-9,Lamp No Price,,,,,0,0"))
    body = response.json()
    assert body["imported"] == 0
    assert body["skipped"] == 1
    assert any("unit_price" in e["message"] for e in body["errors"])


def test_import_bad_number_skips_row(api):
    response = _import(api, _csv("LMP-8,Lamp,Lighting,,NOT_A_NUMBER,,1,0"))
    body = response.json()
    assert body["skipped"] == 1
    assert any("valid number" in e["message"] for e in body["errors"])


def test_import_negative_stock_skips_row(api):
    response = _import(api, _csv("LMP-7,Lamp,,,-1,0,-5,0"))
    body = response.json()
    assert body["skipped"] == 1
    assert any("stock_quantity" in e["message"] for e in body["errors"])


def test_import_unknown_category_skips_row_only(api):
    response = _import(api, _csv("LMP-6,Lamp,Nope Category,,10.00,,1,0"))
    body = response.json()
    assert body["imported"] == 0
    assert body["skipped"] == 1
    assert any("category" in e["message"] for e in body["errors"])
    assert api.client.get("/products").json()["total"] == 0


def test_import_unknown_supplier_skips_row(api):
    api.create_category("Lighting")
    response = _import(api, _csv("LMP-5,Lamp,Lighting,Ghost Supplier,10.00,,1,0"))
    body = response.json()
    assert body["skipped"] == 1
    assert any("supplier" in e["message"] for e in body["errors"])


def test_import_duplicate_sku_within_file(api):
    response = _import(
        api,
        _csv(
            "DUP-1,First Lamp,,,10.00,,1,0",
            "DUP-1,Second Lamp,,,11.00,,2,0",
        ),
    )
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 1
    assert any("inside the file" in e["message"] for e in body["errors"])


def test_import_duplicate_sku_against_database(api):
    api.create_product(sku="DBDUP-1")
    response = _import(api, _csv("DBDUP-1,Another Name,,,10.00,,1,0"))
    body = response.json()
    assert body["imported"] == 0
    assert body["skipped"] == 1
    assert any("already exists" in e["message"] for e in body["errors"])


def test_import_summary_counts_mixed_rows(api):
    api.create_category("Stationery")
    response = _import(
        api,
        _csv(
            "OK-1,Good Item,Stationery,,5.00,1.00,10,2",
            "BAD-1,Bad Item,Missing Category,,5.00,1.00,10,2",
            "OK-2,Also Good,Stationery,,7.00,2.00,5,1",
        ),
    )
    body = response.json()
    assert body["total_rows"] == 3
    assert body["imported"] == 2
    assert body["skipped"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 3  # 1-based file line including header


def test_import_sku_normalization(api):
    response = _import(api, _csv("lower-1,Lower Item,,,1.00,,0,0"))
    body = response.json()
    assert body["imported"] == 1
    assert api.client.get("/products", params={"search": "LOWER-1"}).json()["total"] == 1


def test_export_products(api):
    category = api.create_category("Gadgets")
    api.create_product(sku="EXP-001", name="Exported Widget", category_id=category["id"],
                       stock_quantity=4, low_stock_threshold=2)
    response = api.client.get("/products/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.text
    assert text.splitlines()[0].startswith("sku,name,category")
    assert "EXP-001" in text
    assert "Exported Widget" in text
    assert "Gadgets" in text


def test_export_orders_line_level(api):
    customer = api.create_customer("Export Customer")
    product = api.create_product(stock_quantity=5)
    order = api.create_order(customer["id"], [(product["id"], 2)]).json()
    response = api.client.get("/orders/export.csv")
    assert response.status_code == 200
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("order_number,order_date,customer,status,product_sku")
    assert order["order_number"] in lines[1]
    assert product["sku"] in lines[1]
    assert "Export Customer" in lines[1]


def test_export_movements(api):
    product = api.create_product(stock_quantity=3)
    api.stock_in(product["id"], 5)
    api.stock_out(product["id"], 1)
    response = api.client.get("/inventory/movements/export.csv")
    assert response.status_code == 200
    text = response.text
    assert "movement_id,created_at,product_sku" in text
    assert product["sku"] in text
    assert "OUT" in text


def test_export_sanitizes_csv_injection(api):
    api.create_product(name="=SUM(A1:A2); --")
    response = api.client.get("/products/export.csv")
    assert "'=SUM(A1:A2); --" in response.text
    assert "\n=SUM" not in response.text
