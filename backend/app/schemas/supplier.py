from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=5000)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=5000)


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_count: int = 0
    created_at: datetime
    updated_at: datetime
