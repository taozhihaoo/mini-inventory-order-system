"""Pydantic v2 request/response schemas."""

from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate

__all__ = [
    "CategoryCreate",
    "CategoryOut",
    "CategoryUpdate",
    "CustomerCreate",
    "CustomerOut",
    "CustomerUpdate",
    "Page",
    "ProductCreate",
    "ProductOut",
    "ProductUpdate",
    "SupplierCreate",
    "SupplierOut",
    "SupplierUpdate",
]
