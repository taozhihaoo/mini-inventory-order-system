"""Live API verification script: runs the full demo flow over HTTP.

Usage: python scripts/verify_api.py [base_url]   (default http://127.0.0.1:8010)
Prints PASS/FAIL per step and exits non-zero on any failure.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"

failures: list[str] = []


def call(method: str, path: str, payload: dict | None = None):
    request = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body and response.headers.get("content-type", "").startswith("application/json") else body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(name)


def main() -> int:
    # 1. health
    status, body = call("GET", "/health")
    check("health", status == 200 and body["status"] == "ok")

    # 2. create category/supplier/customer
    status, category = call("POST", "/categories", {"name": f"Verify Cat {id(object())}"})
    check("create category", status == 201)
    status, supplier = call("POST", "/suppliers", {"name": f"Verify Supplier {id(object())}"})
    check("create supplier", status == 201)
    status, customer = call("POST", "/customers", {"name": "Verify Customer", "email": "verify@example.com"})
    check("create customer", status == 201)

    # 3. create product with initial stock
    sku = f"VERIFY-{id(object()) % 100000}"
    status, product = call("POST", "/products", {
        "sku": sku, "name": "Verify Widget", "category_id": category["id"],
        "supplier_id": supplier["id"], "unit_price": "25.00", "cost_price": "12.00",
        "stock_quantity": 8, "low_stock_threshold": 4,
    })
    check("create product (initial stock 8)", status == 201 and product["stock_quantity"] == 8)

    # 4. stock in / out
    status, result = call("POST", f"/products/{product['id']}/stock/in", {"quantity": 5, "note": "verify in"})
    check("stock in 5 -> 13", status == 200 and result["new_quantity"] == 13)
    status, result = call("POST", f"/products/{product['id']}/stock/out", {"quantity": 2, "note": "verify out"})
    check("stock out 2 -> 11", status == 200 and result["new_quantity"] == 11)
    status, result = call("POST", f"/products/{product['id']}/stock/adjust", {"new_quantity": 3, "note": "verify adjust"})
    check("adjust -> 3 (now low stock)", status == 200 and result["new_quantity"] == 3)

    status, low = call("GET", "/inventory/low-stock")
    check("low-stock list contains product", any(p["id"] == product["id"] for p in low))

    # 5. order lifecycle: create -> confirm (stock drop) -> cancel (restore)
    status, order = call("POST", "/orders", {
        "customer_id": customer["id"],
        "items": [{"product_id": product["id"], "quantity": 2}],
    })
    check("create draft order", status == 201 and order["status"] == "draft")
    check("order number format", order["order_number"].startswith("ORD-"))

    status, _ = call("POST", f"/orders/{order['id']}/confirm")
    status2, product_now = call("GET", f"/products/{product['id']}")
    check("confirm order -> stock 3-2=1", status == 200 and product_now["stock_quantity"] == 1)

    status, _ = call("POST", f"/orders/{order['id']}/cancel")
    status2, product_now = call("GET", f"/products/{product['id']}")
    check("cancel order -> stock restored to 3", status == 200 and product_now["stock_quantity"] == 3)

    status, movements = call("GET", f"/products/{product['id']}/stock/movements")
    types = [m["movement_type"] for m in movements["items"]]
    # newest first: cancel-IN, confirm-OUT, adjustment, stock-out, stock-in, initial-IN
    check("movements IN/OUT/ADJ/OUT/IN/IN recorded",
          types == ["IN", "OUT", "ADJUSTMENT", "OUT", "IN", "IN"], str(types))

    # 6. insufficient stock rejected with rollback
    status, draft = call("POST", "/orders", {
        "customer_id": customer["id"],
        "items": [{"product_id": product["id"], "quantity": 999}],
    })
    status, _ = call("POST", f"/orders/{draft['id']}/confirm")
    status2, product_now = call("GET", f"/products/{product['id']}")
    check("insufficient confirm -> 409", status == 409)
    check("rollback: stock still 3", product_now["stock_quantity"] == 3)
    call("POST", f"/orders/{draft['id']}/cancel")

    # 7. csv exports
    for path, needle in [("/products/export.csv", sku), ("/orders/export.csv", order["order_number"]),
                         ("/inventory/movements/export.csv", "movement_type")]:
        request = urllib.request.Request(BASE + path)
        with urllib.request.urlopen(request) as response:
            text = response.read().decode()
            check(f"export {path}", response.status == 200 and needle in text)

    # 8. dashboard
    status, summary = call("GET", "/dashboard/summary")
    check("dashboard summary", status == 200 and summary["total_products"] >= 13)

    print()
    if failures:
        print(f"RESULT: {len(failures)} failure(s): {failures}")
        return 1
    print("RESULT: all live API checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
