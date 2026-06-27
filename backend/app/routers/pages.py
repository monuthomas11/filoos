"""Page-level HTML routes (dashboard, etc.)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud.account import compute_balance, list_accounts
from app.crud.transaction import compute_total_balance, get_recent_transactions
from app.deps import get_current_user, get_db
from app.models.user import User
from app.routers.auth import _issue_delete_account_csrf_token
from app.templates import templates

router = APIRouter()
settings = get_settings()


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request) -> HTMLResponse:
    """Render the Privacy Policy — publicly accessible, no auth required."""
    return templates.TemplateResponse(
        request,
        "privacy.html",
        {
            "title": "Privacy Policy",
            "app_name": settings.app_name,
            "privacy_email": settings.privacy_email,
            "last_updated": "2026-06-27",
            "hosting_region": settings.hosting_region,
            "database_region": settings.database_region,
        },
    )


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request) -> HTMLResponse:
    """Render the Terms of Service — publicly accessible, no auth required."""
    return templates.TemplateResponse(
        request,
        "terms.html",
        {
            "title": "Terms of Service",
            "app_name": settings.app_name,
            "privacy_email": settings.privacy_email,
        },
    )


@router.get("/account/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request, user: User = Depends(get_current_user)
) -> HTMLResponse:
    """Settings page — data export and account deletion."""
    return templates.TemplateResponse(
        request,
        "account/settings.html",
        {"title": "Settings"},
    )


@router.get("/account/delete", response_class=HTMLResponse)
async def delete_account_page(
    request: Request, user: User = Depends(get_current_user)
) -> HTMLResponse:
    """Delete-account confirmation page."""
    csrf_token = _issue_delete_account_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "account/delete.html",
        {"title": "Delete Account", "csrf_token": csrf_token},
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> HTMLResponse:
    """Phase 3 dashboard: shows total balance, per-account cards, recent transactions."""
    accounts = list_accounts(db, active_only=True, show_on_dashboard=True, user_id=user.id)
    balances: dict[int, Decimal] = {}
    for a in accounts:
        balances[a.id] = compute_balance(a, db)
    total_balance = compute_total_balance(accounts, db)
    recent_txns = get_recent_transactions(db, limit=10, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Dashboard",
            "accounts": accounts,
            "balances": balances,
            "total_balance": total_balance,
            "recent_transactions": recent_txns,
        },
    )
