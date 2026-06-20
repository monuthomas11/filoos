"""Forecasting service — EMA + day-of-week seasonality + confidence bands."""

from __future__ import annotations

import datetime
import math
import time
from typing import Any

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.account import list_accounts
from app.crud.transaction import compute_total_balance
from app.models.transaction import Transaction, TransactionType

_forecast_cache: dict[str, tuple[float, Any]] = {}


def _cache_key(scope: str, user_id: int, horizon: int, today: datetime.date) -> str:
    return f"{scope}:{user_id}:{horizon}:{today.isoformat()}"


def _cached_or_compute(
    scope: str, user_id: int, horizon: int, today: datetime.date, ttl: int, fn
) -> Any:
    key = _cache_key(scope, user_id, horizon, today)
    now = time.time()

    # Evict stale entries older than 2× TTL
    stale = [k for k, (ts, _) in _forecast_cache.items() if now - ts >= 2 * ttl]
    for k in stale:
        del _forecast_cache[k]

    if key in _forecast_cache:
        ts, value = _forecast_cache[key]
        if now - ts < ttl:
            return value
    value = fn()
    _forecast_cache[key] = (now, value)
    return value


def _clear_cache() -> None:
    _forecast_cache.clear()


def _daily_series(
    db: Session,
    user_id: int,
    type_filter: TransactionType,
    days: int,
    end_date: datetime.date,
) -> tuple[list[datetime.date], list[float]]:
    """Return (dates, amounts) for the last *days* days ending at *end_date*."""
    start = end_date - datetime.timedelta(days=days - 1)
    rows = (
        db.query(
            Transaction.date,
            func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
        )
        .filter(
            Transaction.date >= start,
            Transaction.date <= end_date,
            Transaction.type == type_filter,
            Transaction.user_id == user_id,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )
    date_map = {r[0]: float(r[1]) for r in rows}
    dates: list[datetime.date] = []
    amounts: list[float] = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        dates.append(d)
        amounts.append(date_map.get(d, 0.0))
    return dates, amounts


def _ema(values: list[float], alpha: float = 0.3) -> list[float]:
    """Exponential moving average."""
    if not values:
        return []
    result: list[float] = []
    current = values[0]
    for v in values:
        current = alpha * v + (1 - alpha) * current
        result.append(current)
    return result


def _seasonal_factors(dates: list[datetime.date], amounts: list[float]) -> dict[int, float]:
    """Day-of-week seasonal adjustment: mean(weekday) - overall_mean."""
    overall_mean = float(np.mean(amounts)) if amounts else 0.0
    weekday_vals: dict[int, list[float]] = {i: [] for i in range(7)}
    for d, v in zip(dates, amounts, strict=True):
        weekday_vals[d.weekday()].append(v)
    seasonal: dict[int, float] = {}
    for wd in range(7):
        vals = weekday_vals[wd]
        seasonal[wd] = float(np.mean(vals)) - overall_mean if vals else 0.0
    return seasonal


def _decompose(
    dates: list[datetime.date],
    amounts: list[float],
    alpha: float = 0.3,
) -> dict[str, Any]:
    """Decompose a time series into trend, seasonality, and residuals.

    Returns dict with trend (list), seasonal (dict[int,float]), residuals
    (list), residual_std (float), trend_end (float).
    """
    has_data = any(a > 0 for a in amounts)
    if not has_data:
        return {
            "trend": [],
            "seasonal": {i: 0.0 for i in range(7)},
            "residuals": [],
            "residual_std": 0.0,
            "trend_end": 0.0,
        }

    trend = _ema(amounts, alpha=alpha)
    seasonal = _seasonal_factors(dates, amounts)

    residuals: list[float] = []
    for d, v, t in zip(dates, amounts, trend, strict=True):
        residuals.append(v - t - seasonal[d.weekday()])

    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0

    return {
        "trend": trend,
        "seasonal": seasonal,
        "residuals": residuals,
        "residual_std": residual_std,
        "trend_end": trend[-1] if trend else 0.0,
    }


def _compute_forecast(
    db: Session,
    user_id: int,
    type_filter: TransactionType,
    horizon: int,
    today: datetime.date | None = None,
) -> dict[str, Any]:
    """Full forecast for a single transaction type.

    Returns dict with horizon, history (list of {date, amount, trend}),
    forecast (list of {date, amount, upper, lower}), residual_std, trend_end.
    """
    from app.config import get_settings

    settings = get_settings()
    history_days = settings.forecast_history_days
    if today is None:
        today = datetime.date.today()

    dates, amounts = _daily_series(db, user_id, type_filter, history_days, today)
    decomposed = _decompose(dates, amounts)
    has_data = bool(decomposed["trend"])

    if not has_data:
        return {
            "horizon": horizon,
            "history": [],
            "forecast": [],
            "residual_std": 0.0,
            "trend_end": 0.0,
        }

    history = [
        {"date": d.isoformat(), "amount": f"{a:.2f}", "trend": f"{t:.2f}"}
        for d, a, t in zip(dates, amounts, decomposed["trend"], strict=True)
    ]

    trend_end = decomposed["trend_end"]
    seasonal = decomposed["seasonal"]
    residual_std = decomposed["residual_std"]
    z = 1.96

    forecast: list[dict] = []
    for i in range(1, horizon + 1):
        d = today + datetime.timedelta(days=i)
        amt = trend_end + seasonal[d.weekday()]
        band = z * residual_std * math.sqrt(i)
        forecast.append(
            {
                "date": d.isoformat(),
                "amount": f"{amt:.2f}",
                "upper": f"{amt + band:.2f}",
                "lower": f"{max(0.0, amt - band):.2f}",
            }
        )

    return {
        "horizon": horizon,
        "history": history,
        "forecast": forecast,
        "residual_std": round(residual_std, 4),
        "trend_end": round(trend_end, 2),
    }


def expense_forecast(
    db: Session,
    user_id: int,
    horizon: int = 30,
    today: datetime.date | None = None,
) -> dict[str, Any]:
    """Forecast daily expenses for the next *horizon* days."""
    if today is None:
        today = datetime.date.today()
    from app.config import get_settings

    settings = get_settings()
    ttl = settings.forecast_cache_ttl_seconds
    return _cached_or_compute(
        "expense",
        user_id,
        horizon,
        today,
        ttl,
        lambda: _compute_forecast(db, user_id, TransactionType.EXPENSE, horizon, today),
    )


def balance_projection(
    db: Session,
    user_id: int,
    horizon: int = 90,
    today: datetime.date | None = None,
) -> dict[str, Any]:
    """Project total balance forward *horizon* days.

    Combines income and expense forecasts, projects daily balances,
    and identifies the runway date (when balance hits zero).
    """
    from app.config import get_settings

    settings = get_settings()
    history_days = settings.forecast_history_days
    if today is None:
        today = datetime.date.today()

    # Current total balance across all user's active accounts (single query)
    accounts = list_accounts(db, active_only=True, user_id=user_id)
    current_balance = compute_total_balance(accounts, db)

    # Decompose income and expense series
    inc_dates, inc_amounts = _daily_series(db, user_id, TransactionType.INCOME, history_days, today)
    exp_dates, exp_amounts = _daily_series(
        db, user_id, TransactionType.EXPENSE, history_days, today
    )

    inc_dec = _decompose(inc_dates, inc_amounts)
    exp_dec = _decompose(exp_dates, exp_amounts)

    inc_trend_end = inc_dec["trend_end"]
    exp_trend_end = exp_dec["trend_end"]
    inc_seasonal = inc_dec["seasonal"]
    exp_seasonal = exp_dec["seasonal"]

    # Combined residual standard deviation for confidence bands
    all_residuals = inc_dec["residuals"] + exp_dec["residuals"]
    combined_std = float(np.std(all_residuals, ddof=1)) if len(all_residuals) > 1 else 0.0

    z = 1.96
    starting_balance = float(current_balance)
    running = starting_balance
    projections: list[dict] = []
    runway: str | None = None

    for i in range(1, horizon + 1):
        d = today + datetime.timedelta(days=i)
        wd = d.weekday()
        income = inc_trend_end + inc_seasonal[wd]
        expense = exp_trend_end + exp_seasonal[wd]
        net = income - expense
        running += net
        band = z * combined_std * math.sqrt(i)
        projections.append(
            {
                "date": d.isoformat(),
                "balance": f"{running:.2f}",
                "upper": f"{running + band:.2f}",
                "lower": f"{running - band:.2f}",
            }
        )
        if runway is None and running <= 0 and starting_balance > 0:
            runway = d.isoformat()

    return {
        "horizon": horizon,
        "current_balance": f"{float(current_balance):.2f}",
        "projections": projections,
        "residual_std": round(combined_std, 4),
        "runway": runway,
    }
