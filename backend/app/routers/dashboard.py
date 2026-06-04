"""Dashboard JSON API routes — used by Chart.js on the dashboard page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud.account import get_account
from app.deps import get_db
from app.services.analytics import (
    balance_history,
    category_breakdown,
    daily_spending,
    monthly_summary,
)

router = APIRouter()


@router.get("/api/dashboard/summary")
async def dashboard_summary(
    year: int | None = Query(None, description="YYYY"),
    month: int | None = Query(None, description="1-12"),
    db: Session = Depends(get_db),
):
    """Monthly income, expense, net, and savings-rate totals."""
    return monthly_summary(db, year, month)


@router.get("/api/dashboard/spending")
async def dashboard_spending(
    range: int = Query(30, alias="range", ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db),
):
    """Daily expense series for the last N days."""
    return {"days": range, "data": daily_spending(db, range)}


@router.get("/api/dashboard/category-breakdown")
async def dashboard_category_breakdown(
    month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Expense totals grouped by type (placeholder until categories exist)."""
    if month:
        parts = month.split("-")
        year = int(parts[0])
        month_int = int(parts[1])
    else:
        year = None
        month_int = None
    return {"month": month or "current", "data": category_breakdown(db, year, month_int)}


@router.get("/api/accounts/{account_id}/balance-history")
async def account_balance_history(
    account_id: int,
    range: int = Query(90, alias="range", ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db),
):
    """Daily running-balance series for a single account."""
    account = get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "account_id": account_id,
        "days": range,
        "data": balance_history(db, account_id, range),
    }
