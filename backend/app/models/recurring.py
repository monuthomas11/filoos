from __future__ import annotations

import datetime
import enum
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import TimestampMixin


class RecurringFrequency(enum.StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurringTransactionType(enum.StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class RecurringRule(Base, TimestampMixin):
    __tablename__ = "recurring_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    type: Mapped[RecurringTransactionType] = mapped_column(
        SAEnum(RecurringTransactionType, name="recurring_transaction_type_enum", create_constraint=True),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    frequency: Mapped[RecurringFrequency] = mapped_column(
        SAEnum(RecurringFrequency, name="recurring_frequency_enum", create_constraint=True),
        nullable=False,
    )
    interval: Mapped[int] = mapped_column(Integer, default=1)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_generated_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    account = relationship("Account")
    category = relationship("Category")
