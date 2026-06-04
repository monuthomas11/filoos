"""Analytics service — helper functions for dashboard data."""

from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType


def monthly_summary(
    db: Session,
    year: int | None = None,
    month: int | None = None,
) -> dict:
    """Return income, expense, net, and savings rate for a given month.

    Defaults to the current month.
    """
    today = datetime.date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    start = datetime.date(year, month, 1)
    if month == 12:
        end = datetime.date(year + 1, 1, 1)
    else:
        end = datetime.date(year, month + 1, 1)

    rows = (
        db.query(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .filter(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.type)
        .all()
    )

    type_totals: dict[TransactionType, Decimal] = {r[0]: r[1] for r in rows}

    income = abs(type_totals.get(TransactionType.INCOME, Decimal("0")))
    expense = abs(type_totals.get(TransactionType.EXPENSE, Decimal("0")))
    net = income - expense
    savings_rate = round(max(0.0, float(net / income) * 100), 1) if income > 0 else None

    return {
        "year": year,
        "month": month,
        "income": str(income),
        "expense": str(expense),
        "net": str(net),
        "savings_rate": savings_rate,
    }


def daily_spending(db: Session, days: int = 30) -> list[dict]:
    """Return a daily expense series (as absolute amounts) for the last *days* days."""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)

    rows = (
        db.query(
            Transaction.date,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .filter(
            Transaction.date >= start,
            Transaction.date <= today,
            Transaction.type == TransactionType.EXPENSE,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )

    date_map = {r[0]: abs(r[1]) for r in rows}
    series: list[dict] = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        series.append({"date": d.isoformat(), "amount": str(date_map.get(d, Decimal("0.00")))})
    return series


def category_breakdown(
    db: Session,
    year: int | None = None,
    month: int | None = None,
) -> list[dict]:
    """Return transaction totals grouped by type as a fallback breakdown.

    Once the Category model exists (Phase 5) this should be updated to group
    by ``Transaction.category_id`` with proper category labels.
    """
    today = datetime.date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    start = datetime.date(year, month, 1)
    if month == 12:
        end = datetime.date(year + 1, 1, 1)
    else:
        end = datetime.date(year, month + 1, 1)

    rows = (
        db.query(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .filter(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.type)
        .all()
    )

    label_map = {
        TransactionType.INCOME: "Income",
        TransactionType.EXPENSE: "Expense",
        TransactionType.TRANSFER: "Transfer",
    }
    return [
        {"label": label_map[r[0]], "amount": str(abs(r[1]))}
        for r in rows
        if r[1] != 0
    ]


def balance_history(
    db: Session,
    account_id: int,
    days: int = 90,
) -> list[dict]:
    """Return a daily running-balance series for *account_id* over *days* days."""
    from app.crud.account import get_account

    account = get_account(db, account_id)
    if account is None:
        return []

    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)

    rows = (
        db.query(
            Transaction.date,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .filter(
            Transaction.account_id == account_id,
            Transaction.date >= start,
            Transaction.date <= today,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )

    prior_sum: Decimal = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id == account_id,
            Transaction.date < start,
        )
        .scalar()
        or Decimal("0")
    )

    running = account.opening_balance + prior_sum
    date_map = {r[0]: r[1] for r in rows}
    series: list[dict] = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        running += date_map.get(d, Decimal("0.00"))
        series.append({"date": d.isoformat(), "balance": str(running)})
    return series
