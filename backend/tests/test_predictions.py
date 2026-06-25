"""Tests for forecasting service and prediction API endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.account import create_account
from app.crud.transaction import create_transaction
from app.models.account import AccountType
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.account import AccountCreate
from app.services.forecasting import (
    _clear_cache,
    _daily_series,
    _decompose,
    _ema,
    _seasonal_factors,
    balance_projection,
    expense_forecast,
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
# Internal helpers
# ------------------------------------------------------------------


def test_ema_simple():
    """Basic EMA computation."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = _ema(values, alpha=0.5)
    assert len(result) == 5
    # Manual: start=1, then 0.5*2+0.5*1=1.5, 0.5*3+0.5*1.5=2.25, ...
    assert result[0] == 1.0
    assert result[1] == 1.5
    assert result[2] == 2.25
    assert result[3] == 3.125
    assert result[4] == 4.0625


def test_ema_empty():
    assert _ema([]) == []


def test_seasonal_factors_all_same():
    """If all days have the same amount, seasonal factors should be zero."""
    from datetime import date

    dates = [date(2026, 1, 5 + i) for i in range(7)]  # Mon-Sun
    amounts = [100.0] * 7
    factors = _seasonal_factors(dates, amounts)
    for wd in range(7):
        assert factors[wd] == 0.0


def test_seasonal_factors():
    """Seasonal factors reflect weekday patterns."""
    from datetime import date

    dates = [date(2026, 1, 5 + i) for i in range(7)]  # Mon-Sun
    # Monday = 200, others = 100
    amounts = [200.0 if d.weekday() == 0 else 100.0 for d in dates]
    factors = _seasonal_factors(dates, amounts)
    overall_mean = sum(amounts) / len(amounts)  # ~114.29
    assert abs(factors[0] - (200.0 - overall_mean)) < 0.01
    assert abs(factors[1] - (100.0 - overall_mean)) < 0.01


def test_daily_series(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="1000")
    _seed_tx(db_session, uid, 1, "-100", TransactionType.EXPENSE, "Coffee", days_ago=0)
    _seed_tx(db_session, uid, 1, "-50", TransactionType.EXPENSE, "Snacks", days_ago=1)

    today = datetime.date.today()
    dates, amounts = _daily_series(db_session, uid, TransactionType.EXPENSE, 7, today)

    assert len(dates) == 7
    assert len(amounts) == 7
    assert dates[-1] == today
    assert amounts[-1] == 100.0  # today's total
    assert amounts[-2] == 50.0  # yesterday's total


def test_daily_series_empty(db_session: Session):
    uid = _seed_user(db_session)
    today = datetime.date.today()
    dates, amounts = _daily_series(db_session, uid, TransactionType.EXPENSE, 7, today)
    assert len(dates) == 7
    assert all(a == 0.0 for a in amounts)


def test_decompose_empty():
    result = _decompose([], [])
    assert result["trend"] == []
    assert result["residual_std"] == 0.0
    assert result["trend_end"] == 0.0


def test_decompose_flat():
    """Flat series → zero residuals."""
    from datetime import date

    dates = [date(2026, 1, 5 + i) for i in range(7)]
    amounts = [100.0] * 7
    result = _decompose(dates, amounts, alpha=0.5)
    assert len(result["trend"]) == 7
    assert result["trend_end"] > 0
    # residuals should be near-zero (flat series)
    assert abs(result["residual_std"]) < 0.01


# ------------------------------------------------------------------
# Forecasting service
# ------------------------------------------------------------------


def test_expense_forecast_empty(db_session: Session):
    """Empty DB should return empty forecast."""
    uid = _seed_user(db_session)
    _clear_cache()
    result = expense_forecast(db_session, uid, horizon=7)
    assert result["horizon"] == 7
    assert result["history"] == []
    assert result["forecast"] == []
    assert result["residual_std"] == 0.0


def test_expense_forecast_with_data(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="10000")
    # Create 14 days of expense data
    for i in range(14):
        _seed_tx(db_session, uid, 1, "-200", TransactionType.EXPENSE, f"Expense {i}", days_ago=i)

    _clear_cache()
    result = expense_forecast(db_session, uid, horizon=7)
    assert result["horizon"] == 7
    assert len(result["history"]) > 0
    assert len(result["forecast"]) == 7
    assert result["residual_std"] > 0
    assert result["trend_end"] > 0

    # Each forecast entry should have date, amount, upper, lower
    for entry in result["forecast"]:
        assert "date" in entry
        assert "amount" in entry
        assert "upper" in entry
        assert "lower" in entry
        assert float(entry["lower"]) <= float(entry["amount"]) <= float(entry["upper"])


def test_expense_forecast_single_type(db_session: Session):
    """Income transactions should not affect expense forecast."""
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="10000")
    # Only income transactions
    for i in range(14):
        _seed_tx(db_session, uid, 1, "5000", TransactionType.INCOME, "Salary", days_ago=i)

    _clear_cache()
    result = expense_forecast(db_session, uid, horizon=7)
    # Should be empty since there are no expenses
    assert result["history"] == []


def test_balance_projection_empty(db_session: Session):
    """Empty DB should return zero balance and no runway."""
    uid = _seed_user(db_session)
    _clear_cache()
    result = balance_projection(db_session, uid, horizon=30)
    assert result["current_balance"] == "0.00"
    assert len(result["projections"]) == 30
    assert result["runway"] is None  # already at zero


def test_balance_projection_with_data(db_session: Session):
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="10000")
    # Income
    for i in range(30):
        _seed_tx(db_session, uid, 1, "5000", TransactionType.INCOME, "Salary", days_ago=i)
    # Expenses
    for i in range(30):
        _seed_tx(db_session, uid, 1, "-2000", TransactionType.EXPENSE, "Rent", days_ago=i)

    _clear_cache()
    result = balance_projection(db_session, uid, horizon=30)
    assert float(result["current_balance"]) > 0
    assert len(result["projections"]) == 30
    for entry in result["projections"]:
        assert "date" in entry
        assert "balance" in entry
        assert "upper" in entry
        assert "lower" in entry


def test_runway_detected(db_session: Session):
    """If spending exceeds income, runway should be set."""
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="10000")
    # Past expenses: 5 days of -1000/day
    for i in range(5):
        _seed_tx(db_session, uid, 1, "-1000", TransactionType.EXPENSE, "Spend", days_ago=i)
    # Current balance ≈ 10000 - 5000 = 5000 (> 0, so runway tracking is active)
    _clear_cache()
    result = balance_projection(db_session, uid, horizon=30)
    # Daily expense estimate ≈ 1000, no income → net -1000/day
    # 5000 / 1000 = 5 days → runway in ~5 days
    assert result["runway"] is not None
    # Should be within the projection window
    assert result["runway"] >= (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


def test_no_runway_with_sufficient_balance(db_session: Session):
    """Sufficient balance and income means no runway."""
    uid = _seed_user(db_session)
    _seed_account(db_session, uid, "Acct", balance="100000")
    # Income exceeds expenses
    for i in range(14):
        _seed_tx(db_session, uid, 1, "10000", TransactionType.INCOME, "Salary", days_ago=i)
    for i in range(14):
        _seed_tx(db_session, uid, 1, "-2000", TransactionType.EXPENSE, "Rent", days_ago=i)

    _clear_cache()
    result = balance_projection(db_session, uid, horizon=30)
    assert result["runway"] is None


# ------------------------------------------------------------------
# HTTP endpoints
# ------------------------------------------------------------------


def test_predictions_expenses_json(client: TestClient):
    _clear_cache()
    response = client.get("/api/predictions/expenses?horizon=7")
    assert response.status_code == 200
    data = response.json()
    assert "horizon" in data
    assert "history" in data
    assert "forecast" in data
    assert data["horizon"] == 7


def test_predictions_expenses_default_horizon(client: TestClient):
    _clear_cache()
    response = client.get("/api/predictions/expenses")
    assert response.status_code == 200
    data = response.json()
    assert data["horizon"] == 30


def test_predictions_expenses_with_data(client: TestClient):
    # Create account + transaction data via HTMX
    client.post("/accounts", data={"name": "Bank", "type": "bank"}, headers={"HX-Request": "true"})
    for i in range(14):
        client.post(
            "/transactions",
            data={
                "type": "expense",
                "account_id": "1",
                "amount": "200",
                "description": f"Test {i}",
                "date": (datetime.date.today() - datetime.timedelta(days=i)).isoformat(),
            },
            headers={"HX-Request": "true"},
        )

    _clear_cache()
    response = client.get("/api/predictions/expenses?horizon=7")
    assert response.status_code == 200
    data = response.json()
    assert len(data["forecast"]) == 7
    for entry in data["forecast"]:
        assert "amount" in entry
        assert "upper" in entry
        assert "lower" in entry


def test_predictions_balance_json(client: TestClient):
    _clear_cache()
    response = client.get("/api/predictions/balance?horizon=7")
    assert response.status_code == 200
    data = response.json()
    assert "current_balance" in data
    assert "projections" in data
    assert "runway" in data
    assert data["horizon"] == 7
    assert len(data["projections"]) == 7


def test_predictions_balance_default_horizon(client: TestClient):
    _clear_cache()
    response = client.get("/api/predictions/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["horizon"] == 90


def test_predictions_invalid_horizon(client: TestClient):
    response = client.get("/api/predictions/expenses?horizon=0")
    assert response.status_code == 422

    response = client.get("/api/predictions/expenses?horizon=999")
    assert response.status_code == 422

    response = client.get("/api/predictions/balance?horizon=0")
    assert response.status_code == 422

    response = client.get("/api/predictions/balance?horizon=999")
    assert response.status_code == 422


def test_dashboard_page_has_prediction_elements(client: TestClient):
    """The dashboard page should have the new prediction UI elements."""
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="balance-trend-chart"' in response.text
    assert 'id="runway-warning"' in response.text
    assert 'id="runway-text"' in response.text
    assert "Balance Trend" in response.text
