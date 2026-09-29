from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=5000)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=5000)


class CustomerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_count: int = 0
    created_at: datetime
    updated_at: datetime
