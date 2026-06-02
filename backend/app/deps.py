"""FastAPI dependencies."""

from __future__ import annotations

from app.database import get_db  # noqa: F401 — re-export for router imports

__all__ = ["get_db"]
