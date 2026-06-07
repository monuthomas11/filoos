"""Prediction JSON API routes — expense forecasts & balance projections."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services.forecasting import balance_projection, expense_forecast

router = APIRouter()


@router.get("/api/predictions/expenses")
async def predictions_expenses(
    horizon: int = Query(30, ge=1, le=365, description="Forecast horizon in days"),
    db: Session = Depends(get_db),
):
    """Daily expense forecast with confidence bands for the next N days."""
    return expense_forecast(db, horizon=horizon)


@router.get("/api/predictions/balance")
async def predictions_balance(
    horizon: int = Query(90, ge=1, le=365, description="Projection horizon in days"),
    db: Session = Depends(get_db),
):
    """Projected total balance with confidence bands and runway detection."""
    return balance_projection(db, horizon=horizon)
