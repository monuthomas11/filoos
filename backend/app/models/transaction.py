"""Transaction model and TransactionType enum."""

from __future__ import annotations

import datetime
import enum
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import TimestampMixin


class TransactionType(enum.StrEnum):
    """Supported transaction types."""

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class Transaction(Base, TimestampMixin):
    """A single financial transaction (expense, income, or transfer leg)."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type_enum", create_constraint=True),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    transfer_pair_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    recurring_rule_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    account = relationship("Account")
    category = relationship("Category", back_populates="transactions")
