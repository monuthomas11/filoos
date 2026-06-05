"""Shared utility helpers."""

from __future__ import annotations

from fastapi import Request


def is_htmx(request: Request) -> bool:
    """Return True if the request was made via HTMX."""
    return request.headers.get("hx-request") == "true"
