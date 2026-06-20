"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db  # noqa: F401 — re-export for router imports
from app.models.user import User


class _NotAuthenticated(HTTPException):
    """Raised when user is not signed in; caught by exception handler in main.py."""


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise _NotAuthenticated(status_code=401, detail="Not signed in")
    user = db.get(User, user_id)
    if not user:
        raise _NotAuthenticated(status_code=401, detail="Stale session")
    return user


def get_current_user_with_db(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> tuple[Session, User]:
    return db, user


__all__ = ["get_db", "get_current_user", "get_current_user_with_db"]
