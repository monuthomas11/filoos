"""Page-level HTML routes (dashboard, etc.)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.crud.account import compute_balance, list_accounts
from app.crud.transaction import get_recent_transactions
from app.deps import get_current_user, get_db
from app.models.user import User
from app.templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> HTMLResponse:
    """Phase 3 dashboard: shows total balance, per-account cards, recent transactions."""
    accounts = list_accounts(db, active_only=True, user_id=user.id)
    balances: dict[int, Decimal] = {}
    for a in accounts:
        balances[a.id] = compute_balance(a, db)
    total_balance = sum(balances.values())
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
