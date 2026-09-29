"""Test setup: fresh in-memory SQLite per test, real app stack, no mocks."""

from __future__ import annotations

import os

# Must be set before app modules are imported: keeps lifespan from touching the
# real database file and points the module-level engine at in-memory SQLite.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class Api:
    """Small factory helper over the test client to keep tests readable."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self._counters: dict[str, int] = {}

    def unique(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]:03d}"

    # ---- master data ---------------------------------------------------

    def create_category(self, name: str | None = None, **fields) -> dict:
        payload = {"name": name or self.unique("Cat "), **fields}
        response = self.client.post("/categories", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    def create_supplier(self, name: str | None = None, **fields) -> dict:
        payload = {"name": name or self.unique("Supplier "), **fields}
        response = self.client.post("/suppliers", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    def create_customer(self, name: str | None = None, **fields) -> dict:
        payload = {"name": name or self.unique("Customer "), **fields}
        response = self.client.post("/customers", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    def create_product(self, sku: str | None = None, name: str | None = None, **fields) -> dict:
        payload = {
            "sku": sku or self.unique("SKU-"),
            "name": name or self.unique("Product "),
            "unit_price": fields.pop("unit_price", "19.90"),
            **fields,
        }
        response = self.client.post("/products", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    # ---- inventory -----------------------------------------------------

    def stock_in(self, product_id: int, quantity: int, note: str | None = None):
        return self.client.post(f"/products/{product_id}/stock/in", json={"quantity": quantity, "note": note})

    def stock_out(self, product_id: int, quantity: int, note: str | None = None):
        return self.client.post(f"/products/{product_id}/stock/out", json={"quantity": quantity, "note": note})

    def stock_adjust(self, product_id: int, new_quantity: int, note: str | None = None):
        return self.client.post(
            f"/products/{product_id}/stock/adjust", json={"new_quantity": new_quantity, "note": note}
        )

    # ---- orders ----------------------------------------------------------

    def create_order(self, customer_id: int, items: list[tuple[int, int]]):
        return self.client.post(
            "/orders",
            json={"customer_id": customer_id, "items": [{"product_id": p, "quantity": q} for p, q in items]},
        )

    def confirm_order(self, order_id: int):
        return self.client.post(f"/orders/{order_id}/confirm")

    def cancel_order(self, order_id: int):
        return self.client.post(f"/orders/{order_id}/cancel")

    def complete_order(self, order_id: int):
        return self.client.post(f"/orders/{order_id}/complete")


@pytest.fixture()
def api(client):
    return Api(client)


@pytest.fixture()
def error_shape():
    def _check(response) -> dict:
        assert "error" in response.json(), response.text
        body = response.json()["error"]
        assert "code" in body and "message" in body
        return body

    return _check
