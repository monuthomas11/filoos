from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.recurring import RecurringFrequency, RecurringTransactionType


class RecurringRuleCreate(BaseModel):
    account_id: int
    category_id: int | None = None
    amount: Decimal = Field(..., gt=0)
    type: RecurringTransactionType
    description: str = Field(..., min_length=1, max_length=200)
    frequency: RecurringFrequency
    interval: int = Field(default=1, ge=1)
    start_date: datetime.date
    end_date: datetime.date | None = None
    day_of_month: int | None = Field(None, ge=1, le=31)
    day_of_week: int | None = Field(None, ge=0, le=6)
    is_active: bool = True


class RecurringRuleUpdate(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    amount: Decimal | None = Field(None, gt=0)
    type: RecurringTransactionType | None = None
    description: str | None = Field(None, min_length=1, max_length=200)
    frequency: RecurringFrequency | None = None
    interval: int | None = Field(None, ge=1)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    day_of_month: int | None = Field(None, ge=1, le=31)
    day_of_week: int | None = Field(None, ge=0, le=6)
    is_active: bool | None = None


class RecurringRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    category_id: int | None = None
    amount: Decimal
    type: RecurringTransactionType
    description: str
    frequency: RecurringFrequency
    interval: int
    start_date: datetime.date
    end_date: datetime.date | None = None
    day_of_month: int | None = None
    day_of_week: int | None = None
    last_generated_date: datetime.date | None = None
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
