"""Shared Jinja2Templates instance used across routers.

Extracted so that both `main.py` and router modules import the same
`templates` object — avoids circular imports and keeps globals in one place.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import get_settings

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals.update(
    app_name=settings.app_name,
    default_currency=settings.default_currency,
    currency_symbol=settings.currency_symbol,
    app_env=settings.app_env,
)
