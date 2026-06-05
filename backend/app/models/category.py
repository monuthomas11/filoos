"""Category model and CategoryType enum."""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CategoryType(enum.StrEnum):
    """Supported category types."""

    EXPENSE = "expense"
    INCOME = "income"


class Category(Base):
    """Transaction category (e.g. Food, Rent, Salary)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    type: Mapped[CategoryType] = mapped_column(
        SAEnum(CategoryType, name="category_type_enum", create_constraint=True),
        nullable=False,
    )
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )

    transactions = relationship("Transaction", back_populates="category", cascade="all, delete-orphan")
