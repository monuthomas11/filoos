"""Pydantic schemas for Account CRUD."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.account import AccountType
from app.utils import validate_hex_color


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    currency: str = Field(default="INR", min_length=3, max_length=3)
    opening_balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    color: str | None = Field(None, max_length=7)
    icon: str | None = Field(None, max_length=50)
    is_active: bool = True

    @field_validator("color")
    @classmethod
    def color_validator(cls, v: str | None) -> str | None:
        return validate_hex_color(v)


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    type: AccountType | None = None
    currency: str | None = Field(None, min_length=3, max_length=3)
    opening_balance: Decimal | None = Field(None, ge=0)
    color: str | None = Field(None, max_length=7)
    icon: str | None = Field(None, max_length=50)
    is_active: bool | None = None

    @field_validator("color")
    @classmethod
    def color_validator(cls, v: str | None) -> str | None:
        return validate_hex_color(v)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: AccountType
    currency: str
    opening_balance: Decimal
    color: str | None = None
    icon: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
