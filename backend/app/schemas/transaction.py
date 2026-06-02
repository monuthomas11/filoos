"""Pydantic schemas for Transaction CRUD."""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    account_id: int
    amount: Decimal = Field(..., gt=0)
    type: TransactionType
    description: str = Field(..., min_length=1, max_length=200)
    notes: str | None = Field(None, max_length=1000)
    date: datetime.date = Field(default_factory=lambda: datetime.date.today())


class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=200)
    notes: str | None = Field(None, max_length=1000)
    date: datetime.date = Field(default_factory=lambda: datetime.date.today())


class TransactionUpdate(BaseModel):
    account_id: int | None = None
    amount: Decimal | None = Field(None, gt=0)
    type: TransactionType | None = None
    description: str | None = Field(None, min_length=1, max_length=200)
    notes: str | None = Field(None, max_length=1000)
    date: datetime.date | None = None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    category_id: int | None = None
    amount: Decimal
    type: TransactionType
    description: str
    notes: str | None = None
    date: datetime.date
    transfer_pair_id: int | None = None
    recurring_rule_id: int | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
