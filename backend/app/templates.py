"""Shared Jinja2Templates instance used across routers.

Extracted so that both `main.py` and router modules import the same
`templates` object — avoids circular imports and keeps globals in one place.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals.update(
    app_name=settings.app_name,
    default_currency=settings.default_currency,
    currency_symbol=settings.currency_symbol,
    app_env=settings.app_env,
    privacy_email=settings.privacy_email,
)


def _current_user(request: Request):
    """Return the current User or None — available in all templates as ``current_user``."""
    from app.database import session_scope
    from app.models.user import User

    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with session_scope() as db:
        user = db.get(User, user_id)
        if user:
            db.expunge(user)
        return user


templates.env.globals["current_user"] = _current_user
