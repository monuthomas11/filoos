"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    """Re-exported for use as `from app.deps import get_db` in routers."""
    yield from _get_db()
