"""Shared utility helpers."""

from __future__ import annotations

import datetime
import re

from fastapi import HTTPException, Request

HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_htmx(request: Request) -> bool:
    """Return True if the request was made via HTMX."""
    return request.headers.get("hx-request") == "true"


def validate_hex_color(v: str | None) -> str | None:
    """Validate that *v* is a hex color string (#RGB or #RRGGBB) or None."""
    if v is not None and not HEX_COLOR_RE.match(v):
        raise ValueError("Color must be a valid hex color (e.g., #4f46e5 or #abc)")
    return v


def parse_date_or_422(date_str: str | None, field_name: str = "date") -> datetime.date | None:
    """Parse an ISO date string, raising 422 on failure."""
    if date_str is None:
        return None
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Invalid {field_name} format (use YYYY-MM-DD)"
        ) from None
