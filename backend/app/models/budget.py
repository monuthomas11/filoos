"""Budget model and BudgetPeriod enum."""

from __future__ import annotations

import datetime
import enum
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import TimestampMixin


class BudgetPeriod(enum.StrEnum):
    """Period over which a budget is measured."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Budget(Base, TimestampMixin):
    """Budget limit per category."""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    period: Mapped[BudgetPeriod] = mapped_column(
        SAEnum(BudgetPeriod, name="budget_period_enum", create_constraint=True),
        nullable=False,
    )
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category = relationship("Category")
