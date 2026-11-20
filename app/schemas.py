"""Pydantic request/response schemas for the educational Luden API."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class BillStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    DECLINED = "Declined"
    PAID = "Paid"
    COMPLETED = "Completed"


class ProductCreate(CamelModel):
    name: str
    description: str = ""
    price: float = Field(..., ge=0.01)
    stock: int = Field(0, ge=0)
    category: str = ""

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 3 or len(trimmed) > 200:
            raise ValueError("name length must be 3..200 after trim")
        return trimmed

    @field_validator("description", "category")
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class ProductPatch(CamelModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0.01)
    stock: int | None = Field(default=None, ge=0)
    category: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> ProductPatch:
        if not self.model_fields_set:
            raise ValueError("PATCH body must include at least one field")
        return self

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("name cannot be null")
        trimmed = value.strip()
        if len(trimmed) < 3 or len(trimmed) > 200:
            raise ValueError("name length must be 3..200 after trim")
        return trimmed

    @field_validator("price", "stock")
    @classmethod
    def reject_null_scalars(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        return value

    @field_validator("description", "category", mode="before")
    @classmethod
    def reject_null_text(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("field cannot be null")
        if isinstance(value, str):
            return value.strip()
        return value


class ProductOut(CamelModel):
    id: int
    name: str
    description: str
    price: float
    stock: int
    category: str
    sales_count: int
    created_at: str


class BillCreate(CamelModel):
    product_ids: list[int] = Field(..., min_length=1)

    @field_validator("product_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if any(pid <= 0 for pid in value):
            raise ValueError("productIds must be positive")
        if len(set(value)) != len(value):
            raise ValueError("productIds must be unique")
        return value


class BillItemOut(CamelModel):
    id: int
    product_id: int
    quantity: int
    price_at_purchase: float
    created_at: str


class BillOut(CamelModel):
    id: int
    user_id: int
    currency: str
    total_amount: float
    status: BillStatus
    created_at: str
    updated_at: str | None
    items: list[BillItemOut]


class StatusPatch(CamelModel):
    status: BillStatus


class UserOut(CamelModel):
    id: int
    username: str
    email: str
    role: str
