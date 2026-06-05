"""Analytics service — helper functions for dashboard data."""

from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
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
    """Return transaction totals grouped by category.

    Falls back to type-based grouping when no categories exist.
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

    # Try category-based grouping first
    cat_rows = (
        db.query(
            Category.name,
            Category.color,
            func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type != TransactionType.TRANSFER,
        )
        .group_by(Category.id, Category.name, Category.color)
        .all()
    )

    # Check if any transactions have categories assigned
    if any(name is not None for name, _, _ in cat_rows):
        broken = cat_rows
    else:
        broken = None

    if broken is not None:
        return [
            {"label": name or "Uncategorized", "color": color or "#737373", "amount": str(amount)}
            for name, color, amount in broken
            if amount > 0
        ]

    # Fallback: group by transaction type
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
    palette = {TransactionType.INCOME: "#16a34a", TransactionType.EXPENSE: "#dc2626", TransactionType.TRANSFER: "#4f46e5"}
    return [
        {"label": label_map[r[0]], "color": palette[r[0]], "amount": str(abs(r[1]))}
        for r in rows
        if r[1] != 0
    ]


def budget_progress(
    db: Session,
    year: int | None = None,
    month: int | None = None,
) -> list[dict]:
    """Return budget progress for each active budget in a given month.

    Returns category name, budget amount, spent amount, percentage, remaining.
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

    budgets = (
        db.query(Budget)
        .filter(Budget.is_active.is_(True), Budget.start_date <= end)
        .all()
    )

    # Batch-fetch spending for all budget categories in one query
    category_ids = [b.category_id for b in budgets]
    spending_rows = (
        db.query(
            Transaction.category_id,
            func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
        )
        .filter(
            Transaction.category_id.in_(category_ids),
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == TransactionType.EXPENSE,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    spending_map = {row[0]: Decimal(str(row[1])) for row in spending_rows}

    results: list[dict] = []
    for budget in budgets:
        spent_decimal = spending_map.get(budget.category_id, Decimal("0"))
        percentage = round(float(spent_decimal / budget.amount) * 100, 1) if budget.amount > 0 else 0
        remaining = budget.amount - spent_decimal

        cat_name = budget.category.name if budget.category else "Unknown"
        cat_color = budget.category.color or "#4f46e5"

        results.append({
            "budget_id": budget.id,
            "category_id": budget.category_id,
            "category_name": cat_name,
            "category_color": cat_color,
            "amount": f"{budget.amount:.2f}",
            "spent": f"{spent_decimal:.2f}",
            "percentage": percentage,
            "remaining": f"{remaining:.2f}",
            "over_budget": remaining < 0,
        })

    return sorted(results, key=lambda r: r["category_name"])


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
