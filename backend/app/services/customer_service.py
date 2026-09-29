"""Customer business logic."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Customer
from app.repositories.customer import CustomerRepository
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.exceptions import NotFoundError, ReferencedError


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CustomerRepository(db)

    def list_customers(self, *, search: str | None, page: int, page_size: int) -> Page[Customer]:
        rows, total = self.repo.list(search=search, offset=(page - 1) * page_size, limit=page_size)
        items = [row[0] for row in rows]
        return Page.build(items=items, total=total, page=page, page_size=page_size)

    def get_customer(self, customer_id: int) -> Customer:
        customer = self.repo.get(customer_id)
        if customer is None:
            raise NotFoundError(f"Customer {customer_id} not found.")
        return customer

    def create_customer(self, data: CustomerCreate) -> Customer:
        return self.repo.add(
            Customer(
                name=data.name.strip(),
                email=data.email,
                phone=data.phone,
                notes=data.notes,
            )
        )

    def update_customer(self, customer_id: int, data: CustomerUpdate) -> Customer:
        customer = self.get_customer(customer_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            customer.name = changes["name"].strip()
        for field in ("email", "phone", "notes"):
            if field in changes:
                setattr(customer, field, changes[field])
        self.db.flush()
        return customer

    def delete_customer(self, customer_id: int) -> None:
        customer = self.get_customer(customer_id)
        used_by = self.repo.count_orders(customer.id)
        if used_by:
            raise ReferencedError(
                f"Customer '{customer.name}' has {used_by} order(s) and cannot be deleted."
            )
        self.repo.delete(customer)

    def order_count(self, customer_id: int) -> int:
        self.get_customer(customer_id)
        return self.repo.count_orders(customer_id)
