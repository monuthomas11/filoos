"""Account model and AccountType enum."""

from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models import TimestampMixin


class AccountType(enum.StrEnum):
    """Supported account types."""

    CASH = "cash"
    BANK = "bank"
    CREDIT_CARD = "credit_card"
    SAVINGS = "savings"
    INVESTMENT = "investment"


# Default colours per account type (used when no colour is provided).
ACCOUNT_TYPE_COLORS: dict[AccountType, str] = {
    AccountType.CASH: "#16a34a",
    AccountType.BANK: "#4f46e5",
    AccountType.CREDIT_CARD: "#e11d48",
    AccountType.SAVINGS: "#d97706",
    AccountType.INVESTMENT: "#7c3aed",
}


class Account(Base, TimestampMixin):
    """Financial account (cash, bank, credit card, savings, investment)."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        SAEnum(AccountType, name="account_type_enum", create_constraint=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
