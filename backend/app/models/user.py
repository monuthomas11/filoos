"""User model for Google SSO-authenticated users."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models import TimestampMixin


class User(Base, TimestampMixin):
    """A Google-authenticated user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
