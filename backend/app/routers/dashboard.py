"""Dashboard JSON API routes — used by Chart.js on the dashboard page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud.account import get_account
from app.deps import get_db
from app.services.analytics import (
    balance_history,
    budget_progress,
    category_breakdown,
    daily_spending,
    monthly_summary,
)

router = APIRouter()


@router.get("/api/dashboard/summary")
async def dashboard_summary(
    year: int | None = Query(None, description="YYYY"),
    month: int | None = Query(None, description="1-12"),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override: start YYYY-MM-DD"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override: end YYYY-MM-DD (exclusive)"),
    db: Session = Depends(get_db),
):
    """Monthly income, expense, net, and savings-rate totals for a period."""
    return monthly_summary(db, year, month, start_date, end_date)


@router.get("/api/dashboard/spending")
async def dashboard_spending(
    range: int = Query(30, alias="range", ge=1, le=365, description="Number of days (ignored if start_date/end_date set)"),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override start YYYY-MM-DD"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override end YYYY-MM-DD (exclusive)"),
    db: Session = Depends(get_db),
):
    """Daily expense series for the last N days or a custom date range."""
    return {"days": range, "data": daily_spending(db, range, start_date, end_date)}


@router.get("/api/dashboard/category-breakdown")
async def dashboard_category_breakdown(
    year: int | None = Query(None, description="YYYY"),
    month: int | None = Query(None, description="1-12"),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override start YYYY-MM-DD"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override end YYYY-MM-DD (exclusive)"),
    db: Session = Depends(get_db),
):
    """Expense totals grouped by category for a period."""
    if start_date and end_date:
        return {"month": "current", "data": category_breakdown(db, start_date=start_date, end_date=end_date)}
    return {"month": f"{year}-{month:02d}" if year and month else "current", "data": category_breakdown(db, year, month)}


@router.get("/api/dashboard/budgets")
async def dashboard_budgets(
    year: int | None = Query(None, description="YYYY"),
    month: int | None = Query(None, description="1-12"),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override start YYYY-MM-DD"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Override end YYYY-MM-DD (exclusive)"),
    db: Session = Depends(get_db),
):
    """Budget progress for a period (defaults to current month)."""
    return {"data": budget_progress(db, year, month, start_date, end_date)}


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
