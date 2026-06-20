"""ORM models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def _utcnow() -> datetime:
    """Current UTC datetime (naive, for SQLite compatibility)."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    """Mixin adding `created_at` and `updated_at` columns."""

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:  # noqa: N805
        return mapped_column(DateTime, default=_utcnow)

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:  # noqa: N805
        return mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


from app.models.account import Account  # noqa: E402, F401 — Phase 2
from app.models.budget import Budget, BudgetPeriod  # noqa: E402, F401 — Phase 5
from app.models.category import Category, CategoryType  # noqa: E402, F401 — Phase 5
from app.models.recurring import RecurringFrequency, RecurringRule  # noqa: E402, F401 — Phase 6
from app.models.transaction import Transaction, TransactionType  # noqa: E402, F401 — Phase 3
from app.models.user import User  # noqa: E402, F401 — Phase 3
