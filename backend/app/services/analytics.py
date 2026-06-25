"""Analytics service — helper functions for dashboard data."""

from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetPeriod
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction, TransactionType


def _resolve_date_range(
    start_date: str | None,
    end_date: str | None,
    year: int | None,
    month: int | None,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Convert start_date/end_date or year/month to a date range.

    If start_date/end_date are provided they take priority.
    If year/month are provided (or defaults), uses that calendar month.
    If none are provided, returns (None, None) — caller should skip date filtering.
    Returns (start, end) where end is exclusive.
    """
    if start_date and end_date:
        return datetime.date.fromisoformat(start_date), datetime.date.fromisoformat(end_date)
    if year is None and month is None:
        return None, None
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
    return start, end


def _get_period_bounds(
    year: int, month: int, period: BudgetPeriod
) -> tuple[datetime.date, datetime.date]:
    """Return (start, end) date bounds for the given period within the reference month."""
    if period == BudgetPeriod.MONTHLY:
        start = datetime.date(year, month, 1)
        end = datetime.date(year + 1, 1, 1) if month == 12 else datetime.date(year, month + 1, 1)
    elif period == BudgetPeriod.WEEKLY:
        first = datetime.date(year, month, 1)
        start = first - datetime.timedelta(days=first.weekday())
        end = start + datetime.timedelta(weeks=1)
    elif period == BudgetPeriod.YEARLY:
        start = datetime.date(year, 1, 1)
        end = datetime.date(year + 1, 1, 1)
    return start, end


def monthly_summary(
    db: Session,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return income, expense, net, and savings rate for a given period.

    Accepts either (year, month) or (start_date, end_date) to define the range.
    Defaults to the current month if neither is provided.
    """
    start, end = _resolve_date_range(start_date, end_date, year, month)

    query = db.query(
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0),
    ).filter(Transaction.user_id == user_id)
    if start is not None and end is not None:
        query = query.filter(Transaction.date >= start, Transaction.date < end)
    rows = query.group_by(Transaction.type).all()

    type_totals: dict[TransactionType, Decimal] = {r[0]: r[1] for r in rows}

    income = abs(type_totals.get(TransactionType.INCOME, Decimal("0")))
    expense = abs(type_totals.get(TransactionType.EXPENSE, Decimal("0")))
    net = income - expense
    savings_rate = round(max(0.0, float(net / income) * 100), 1) if income > 0 else None

    return {
        "year": start.year if start else None,
        "month": start.month if start else None,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "income": str(income),
        "expense": str(expense),
        "net": str(net),
        "savings_rate": savings_rate,
    }


def daily_spending(
    db: Session,
    user_id: int,
    days: int = 30,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Return a daily expense series (as absolute amounts) for a period.

    Accepts either *days* (looking back from today) or *start_date*/*end_date*
    to define the range. Defaults to the last 30 days.
    """
    today = datetime.date.today()
    if start_date and end_date:
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)
    else:
        start = today - datetime.timedelta(days=days - 1)
        end = today + datetime.timedelta(days=1)
    days_count = (end - start).days

    rows = (
        db.query(
            Transaction.date,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.user_id == user_id,
        )
        .group_by(Transaction.date)
        .order_by(Transaction.date)
        .all()
    )

    date_map = {r[0]: abs(r[1]) for r in rows}
    series: list[dict] = []
    for i in range(days_count):
        d = start + datetime.timedelta(days=i)
        series.append({"date": d.isoformat(), "amount": str(date_map.get(d, Decimal("0.00")))})
    return series


def category_breakdown(
    db: Session,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Return transaction totals grouped by category.

    Falls back to type-based grouping when no categories exist.
    Accepts either (year, month) or (start_date, end_date).
    """
    start, end = _resolve_date_range(start_date, end_date, year, month)

    # Try category-based grouping first
    cat_query = db.query(
        Category.name,
        Category.color,
        func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
    ).outerjoin(Transaction, Transaction.category_id == Category.id)
    cat_query = cat_query.filter(Transaction.user_id == user_id)
    if start is not None and end is not None:
        cat_query = cat_query.filter(Transaction.date >= start, Transaction.date < end)
    cat_query = cat_query.filter(
        Transaction.type != TransactionType.TRANSFER,
        Category.type == CategoryType.EXPENSE,
    )
    cat_rows = cat_query.group_by(Category.id, Category.name, Category.color).all()

    # Check if any transactions have categories assigned
    if any(name is not None for name, _, _ in cat_rows):
        broken = cat_rows
    else:
        broken = None

    if broken is not None:
        return [
            {
                "label": name or "Uncategorized",
                "color": color or "#737373",
                "amount": f"{float(amount):.2f}",
            }
            for name, color, amount in broken
            if amount > 0
        ]

    # Fallback: group by transaction type
    fallback_query = db.query(
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0),
    ).filter(Transaction.user_id == user_id)
    if start is not None and end is not None:
        fallback_query = fallback_query.filter(Transaction.date >= start, Transaction.date < end)
    rows = fallback_query.group_by(Transaction.type).all()

    label_map = {
        TransactionType.INCOME: "Income",
        TransactionType.EXPENSE: "Expense",
        TransactionType.TRANSFER: "Transfer",
    }
    palette = {
        TransactionType.INCOME: "#16a34a",
        TransactionType.EXPENSE: "#dc2626",
        TransactionType.TRANSFER: "#4f46e5",
    }
    return [
        {"label": label_map[r[0]], "color": palette[r[0]], "amount": str(abs(r[1]))}
        for r in rows
        if r[1] != 0
    ]


def budget_progress(
    db: Session,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Return budget progress for each active budget in a given period.

    Returns category name, budget amount, spent amount, percentage, remaining.
    Accepts either (year, month) or (start_date, end_date).
    """
    today = datetime.date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    budgets = db.query(Budget).filter(Budget.is_active.is_(True), Budget.user_id == user_id).all()

    # If explicit date range is given, use it directly (ignore budget periods)
    if start_date and end_date:
        s = datetime.date.fromisoformat(start_date)
        e = datetime.date.fromisoformat(end_date)
        cat_ids = [b.category_id for b in budgets]
        if not cat_ids:
            return []
        rows = (
            db.query(
                Transaction.category_id,
                func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
            )
            .filter(
                Transaction.category_id.in_(cat_ids),
                Transaction.date >= s,
                Transaction.date < e,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.user_id == user_id,
            )
            .group_by(Transaction.category_id)
            .all()
        )
        spending_map = {cat_id: Decimal(str(total)) for cat_id, total in rows}
    else:
        # Group budgets by period and fetch spending per group
        from collections import defaultdict

        by_period: dict[BudgetPeriod, list[Budget]] = defaultdict(list)
        for b in budgets:
            by_period[b.period].append(b)

        spending_map: dict[int, Decimal] = {}
        for period, group in by_period.items():
            period_start, period_end = _get_period_bounds(year, month, period)
            cat_ids = [b.category_id for b in group]
            rows = (
                db.query(
                    Transaction.category_id,
                    func.coalesce(func.sum(func.abs(Transaction.amount)), 0),
                )
                .filter(
                    Transaction.category_id.in_(cat_ids),
                    Transaction.date >= period_start,
                    Transaction.date < period_end,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.user_id == user_id,
                )
                .group_by(Transaction.category_id)
                .all()
            )
            for cat_id, total in rows:
                spending_map[cat_id] = Decimal(str(total))

    results: list[dict] = []
    for budget in budgets:
        spent_decimal = spending_map.get(budget.category_id, Decimal("0"))
        percentage = (
            round(float(spent_decimal / budget.amount) * 100, 1) if budget.amount > 0 else 0
        )
        remaining = budget.amount - spent_decimal

        cat_name = budget.category.name if budget.category else "Unknown"
        cat_color = budget.category.color or "#4f46e5"

        results.append(
            {
                "budget_id": budget.id,
                "category_id": budget.category_id,
                "category_name": cat_name,
                "category_color": cat_color,
                "amount": f"{budget.amount:.2f}",
                "spent": f"{spent_decimal:.2f}",
                "percentage": percentage,
                "remaining": f"{remaining:.2f}",
                "over_budget": remaining < 0,
            }
        )

    return sorted(results, key=lambda r: r["category_name"])


def balance_history(
    db: Session,
    account_id: int,
    user_id: int,
    days: int = 90,
) -> list[dict]:
    """Return a daily running-balance series for *account_id* over *days* days."""
    from app.crud.account import get_account

    account = get_account(db, account_id, user_id=user_id)
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

    prior_sum: Decimal = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.account_id == account_id,
        Transaction.date < start,
    ).scalar() or Decimal("0")

    running = account.opening_balance + prior_sum
    date_map = {r[0]: r[1] for r in rows}
    series: list[dict] = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        running += date_map.get(d, Decimal("0.00"))
        series.append({"date": d.isoformat(), "balance": str(running)})
    return series
