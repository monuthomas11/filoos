"""Pydantic schemas for Budget CRUD."""

from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.budget import BudgetPeriod


class BudgetCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(..., gt=0)
    period: BudgetPeriod
    start_date: datetime.date
    is_active: bool = True


class BudgetUpdate(BaseModel):
    category_id: int | None = None
    amount: Decimal | None = Field(None, gt=0)
    period: BudgetPeriod | None = None
    start_date: datetime.date | None = None
    is_active: bool | None = None


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    amount: Decimal
    period: BudgetPeriod
    start_date: datetime.date
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
