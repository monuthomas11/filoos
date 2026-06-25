"""Tests for dashboard API endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.account import create_account
from app.crud.category import create_category
from app.crud.transaction import create_transaction
from app.models.account import AccountType
from app.models.category import CategoryType
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.account import AccountCreate
from app.schemas.category import CategoryCreate
from app.services.analytics import (
    balance_history,
    balance_trend,
    category_breakdown,
    daily_spending,
    monthly_summary,
)


def _seed_user(db: Session) -> int:
    user = User(email="test@example.com", name="Test User", google_sub="test-sub")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id


def _seed_account(
    db: Session,
    user_id: int,
    name: str = "Test",
    type_: AccountType = AccountType.BANK,
    balance: str = "0",
) -> None:
    create_account(
        db,
        AccountCreate(name=name, type=type_, opening_balance=Decimal(balance)),
        user_id=user_id,
    )


def _seed_tx(
    db: Session,
    user_id: int,
    account_id: int,
    amount: str,
    type_: TransactionType,
    description: str,
    days_ago: int = 0,
) -> None:
    date = datetime.date.today() - datetime.timedelta(days=days_ago)
    create_transaction(
        db=db,
        account_id=account_id,
        amount=Decimal(amount),
        type_=type_,
        description=description,
        date=date,
        user_id=user_id,
    )


# ------------------------------------------------------------------
# Services
# ------------------------------------------------------------------


def test_monthly_summary_empty(db_session: Session):
    uid = _seed_user(db_session)
    result = monthly_summary(db_session, uid)
    assert result["income"] == "0"
    assert result["expense"] == "0"
    assert result["net"] == "0"
    assert result["savings_rate"] is None


def test_monthly_summary_with_data(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")
    _seed_tx(db_session, uid, 1, "5000", TransactionType.INCOME, "Salary", days_ago=0)
    _seed_tx(db_session, uid, 1, "-2000", TransactionType.EXPENSE, "Rent", days_ago=0)
    _seed_tx(db_session, uid, 1, "-500", TransactionType.EXPENSE, "Groceries", days_ago=0)

    result = monthly_summary(db_session, uid)
    assert result["income"] == "5000.00"
    assert result["expense"] == "2500.00"
    assert result["net"] == "2500.00"
    assert result["savings_rate"] == 50.0


def test_daily_spending(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")
    _seed_tx(db_session, uid, 1, "-100", TransactionType.EXPENSE, "Coffee", days_ago=0)
    _seed_tx(db_session, uid, 1, "-200", TransactionType.EXPENSE, "Lunch", days_ago=0)
    _seed_tx(db_session, uid, 1, "-50", TransactionType.EXPENSE, "Snacks", days_ago=1)

    series = daily_spending(db_session, uid, days=7)
    assert len(series) == 7
    # Today should have 300 spending
    today_str = datetime.date.today().isoformat()
    today_entry = next(s for s in series if s["date"] == today_str)
    assert today_entry["amount"] == "300.00"
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    yesterday_entry = next(s for s in series if s["date"] == yesterday_str)
    assert yesterday_entry["amount"] == "50.00"
    # All other days should be zero
    for s in series:
        if s["date"] not in (today_str, yesterday_str):
            assert s["amount"] == "0.00", f"{s['date']}: {s['amount']}"


def test_category_breakdown(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")
    _seed_tx(db_session, uid, 1, "5000", TransactionType.INCOME, "Salary", days_ago=0)
    _seed_tx(db_session, uid, 1, "-2000", TransactionType.EXPENSE, "Rent", days_ago=0)
    _seed_tx(db_session, uid, 1, "-500", TransactionType.EXPENSE, "Food", days_ago=0)

    breakdown = category_breakdown(db_session, uid)
    assert len(breakdown) == 2  # income and expense (no transfers)
    labels = {b["label"] for b in breakdown}
    assert "Income" in labels
    assert "Expense" in labels
    income = next(b for b in breakdown if b["label"] == "Income")
    expense = next(b for b in breakdown if b["label"] == "Expense")
    assert income["amount"] == "5000.00"
    assert expense["amount"] == "2500.00"


def test_category_breakdown_with_categories(db_session: Session):
    """When transactions have categories, breakdown should group by category."""
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")

    food = create_category(
        db_session,
        CategoryCreate(name="Food", type=CategoryType.EXPENSE, color="#ff0000"),
        user_id=uid,
    )
    rent = create_category(
        db_session,
        CategoryCreate(name="Rent", type=CategoryType.EXPENSE, color="#00ff00"),
        user_id=uid,
    )
    salary = create_category(
        db_session,
        CategoryCreate(name="Salary", type=CategoryType.INCOME, color="#0000ff"),
        user_id=uid,
    )

    create_transaction(
        db_session,
        account_id=1,
        amount=Decimal("5000"),
        type_=TransactionType.INCOME,
        description="Paycheck",
        date=datetime.date.today(),
        category_id=salary.id,
        user_id=uid,
    )
    create_transaction(
        db_session,
        account_id=1,
        amount=Decimal("-2000"),
        type_=TransactionType.EXPENSE,
        description="Rent",
        date=datetime.date.today(),
        category_id=rent.id,
        user_id=uid,
    )
    create_transaction(
        db_session,
        account_id=1,
        amount=Decimal("-500"),
        type_=TransactionType.EXPENSE,
        description="Groceries",
        date=datetime.date.today(),
        category_id=food.id,
        user_id=uid,
    )

    breakdown = category_breakdown(db_session, uid)
    labels = {b["label"] for b in breakdown}
    assert "Food" in labels
    assert "Rent" in labels
    assert "Salary" not in labels
    assert "Income" not in labels
    assert "Expense" not in labels

    food_b = next(b for b in breakdown if b["label"] == "Food")
    assert food_b["amount"] == "500.00"
    assert food_b["color"] == "#ff0000"


def test_category_breakdown_mixed(db_session: Session):
    """Categories with transactions + uncategorized transactions coexist."""
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")

    food = create_category(
        db_session,
        CategoryCreate(name="Food", type=CategoryType.EXPENSE, color="#ff0000"),
        user_id=uid,
    )

    create_transaction(
        db_session,
        account_id=1,
        amount=Decimal("-300"),
        type_=TransactionType.EXPENSE,
        description="Groceries",
        date=datetime.date.today(),
        category_id=food.id,
        user_id=uid,
    )
    create_transaction(
        db_session,
        account_id=1,
        amount=Decimal("-200"),
        type_=TransactionType.EXPENSE,
        description="Misc",
        date=datetime.date.today(),
        category_id=None,
        user_id=uid,
    )

    breakdown = category_breakdown(db_session, uid)
    labels = {b["label"] for b in breakdown}
    assert "Food" in labels
    food_b = next(b for b in breakdown if b["label"] == "Food")
    assert food_b["amount"] == "300.00"


def test_balance_history(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")
    _seed_tx(db_session, uid, 1, "500", TransactionType.INCOME, "Deposit", days_ago=2)
    _seed_tx(db_session, uid, 1, "-200", TransactionType.EXPENSE, "Withdraw", days_ago=1)

    history = balance_history(db_session, 1, uid, days=5)
    assert len(history) == 5
    # Day 0 (5 days ago): opening 1000
    # Day 2: +500 = 1500
    # Day 4 (yesterday): -200 = 1300
    # Today: no tx = 1300
    day0 = next(
        s
        for s in history
        if s["date"] == (datetime.date.today() - datetime.timedelta(days=4)).isoformat()
    )
    assert day0["balance"] == "1000.00"
    day_with_deposit = next(
        s
        for s in history
        if s["date"] == (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    )
    assert day_with_deposit["balance"] == "1500.00"


def test_balance_history_nonexistent_account(db_session: Session):
    uid = _seed_user(db_session)
    history = balance_history(db_session, 999, uid, days=7)
    assert history == []


# ------------------------------------------------------------------
# HTTP endpoints
# ------------------------------------------------------------------


def test_dashboard_summary_json(client: TestClient):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "income" in data
    assert "expense" in data
    assert "net" in data
    assert "savings_rate" in data


def test_dashboard_summary_with_data(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank"}, headers={"HX-Request": "true"})
    client.post(
        "/transactions",
        data={
            "type": "income",
            "account_id": "1",
            "amount": "10000",
            "description": "Salary",
            "date": datetime.date.today().isoformat(),
        },
        headers={"HX-Request": "true"},
    )
    client.post(
        "/transactions",
        data={
            "type": "expense",
            "account_id": "1",
            "amount": "3000",
            "description": "Rent",
            "date": datetime.date.today().isoformat(),
        },
        headers={"HX-Request": "true"},
    )

    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["income"] == "10000.00"
    assert data["expense"] == "3000.00"
    assert data["net"] == "7000.00"
    assert data["savings_rate"] == 70.0


def test_dashboard_summary_with_year_month(client: TestClient):
    """Pass explicit year/month params."""
    response = client.get("/api/dashboard/summary?year=2026&month=6")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2026
    assert data["month"] == 6


def test_dashboard_spending_json(client: TestClient):
    response = client.get("/api/dashboard/spending?range=7")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 7


def test_dashboard_category_breakdown(client: TestClient):
    response = client.get("/api/dashboard/category-breakdown")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_dashboard_category_breakdown_with_month(client: TestClient):
    response = client.get("/api/dashboard/category-breakdown?year=2026&month=6")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_dashboard_category_breakdown_invalid_month(client: TestClient):
    response = client.get("/api/dashboard/category-breakdown?month=abc")
    assert response.status_code == 422

    response = client.get("/api/dashboard/category-breakdown?month=xyz")
    assert response.status_code == 422


def test_balance_history_json(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank"}, headers={"HX-Request": "true"})
    response = client.get("/api/accounts/1/balance-history?range=7")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == 1
    assert data["days"] == 7
    assert len(data["data"]) == 7


def test_balance_history_not_found(client: TestClient):
    response = client.get("/api/accounts/999/balance-history")
    assert response.status_code == 404


def test_dashboard_page_has_chart_containers(client: TestClient):
    """The dashboard page should have canvas elements for charts."""
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="spending-chart"' in response.text
    assert 'id="category-chart"' in response.text
    assert 'id="kpi-income"' in response.text
    assert 'id="kpi-expense"' in response.text
    assert 'id="balance-trend-chart"' in response.text


def test_balance_trend_empty(db_session: Session):
    uid = _seed_user(db_session)
    result = balance_trend(db_session, uid)
    assert result["current_balance"] == "0.00"
    assert result["previous_balance"] == "0.00"
    assert result["change_pct"] == 0.0
    assert result["series"] == []


def test_balance_trend_with_transactions(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Bank", AccountType.BANK, "50000")

    today = datetime.date.today()
    _seed_tx(db_session, uid, 1, "-1000", TransactionType.EXPENSE, "Rent", days_ago=2)
    _seed_tx(db_session, uid, 1, "3000", TransactionType.INCOME, "Salary", days_ago=5)

    result = balance_trend(db_session, uid)
    assert float(result["current_balance"]) == 52000
    assert isinstance(result["series"], list)
    assert len(result["series"]) > 0
    assert "date" in result["series"][0]
    assert "balance" in result["series"][0]


def test_balance_trend_json(client: TestClient):
    response = client.get("/api/dashboard/balance-trend")
    assert response.status_code == 200
    data = response.json()
    assert "current_balance" in data
    assert "previous_balance" in data
    assert "change_pct" in data
    assert "series" in data


def test_balance_trend_series_format(client: TestClient):
    """Each series entry must have a valid ISO date and numeric balance for tooltip consistency."""
    response = client.get("/api/dashboard/balance-trend")
    assert response.status_code == 200
    data = response.json()
    for entry in data["series"]:
        assert "date" in entry
        assert "balance" in entry
        # date must be parseable YYYY-MM-DD
        datetime.date.fromisoformat(entry["date"])
        # balance must be a valid decimal string
        float(entry["balance"])


def test_balance_projection_series_format(client: TestClient):
    """Projection entries must have valid dates and numeric balances for tooltip consistency."""
    response = client.get("/api/predictions/balance?horizon=30")
    assert response.status_code == 200
    data = response.json()
    assert "projections" in data
    for entry in data["projections"]:
        assert "date" in entry
        assert "balance" in entry
        datetime.date.fromisoformat(entry["date"])
        float(entry["balance"])


def test_dashboard_chart_tooltip_config(client: TestClient):
    """Dashboard HTML must contain tooltip config that handles null values and index mode."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Tooltip filter to skip null values
    assert "filter: function (c)" in html
    assert "c.parsed.y !== null" in html
    # Interaction mode index + no intersect for consistent hover
    assert "mode: 'index'" in html
    assert "intersect: false" in html
