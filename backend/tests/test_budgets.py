"""Tests for the Budget model, CRUD, budget_progress, and HTTP endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.budget import (
    create_budget,
    delete_budget,
    get_budget,
    list_budgets,
    update_budget,
)
from app.crud.category import create_category
from app.crud.transaction import create_transaction
from app.models.budget import BudgetPeriod
from app.models.transaction import TransactionType
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.schemas.category import CategoryCreate
from app.services.analytics import budget_progress


def _seed_cat(db: Session, name: str = "Food", type_: str = "expense", color: str = "#16a34a"):
    return create_category(db, CategoryCreate(name=name, type=type_, color=color))


# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------


def test_budget_period_enum():
    assert BudgetPeriod.WEEKLY.value == "weekly"
    assert BudgetPeriod.MONTHLY.value == "monthly"
    assert BudgetPeriod.YEARLY.value == "yearly"


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_create_and_read_budget(db_session: Session):
    cat = _seed_cat(db_session, "Food")
    data = BudgetCreate(
        category_id=cat.id,
        amount=Decimal("10000"),
        period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1),
    )
    budget = create_budget(db_session, data)
    assert budget.id is not None
    assert budget.category_id == cat.id
    assert budget.amount == Decimal("10000")
    assert budget.period == BudgetPeriod.MONTHLY
    assert budget.is_active is True

    fetched = get_budget(db_session, budget.id)
    assert fetched is not None
    assert fetched.amount == Decimal("10000")


def test_list_budgets(db_session: Session):
    cat = _seed_cat(db_session, "Food")
    create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("5000"), period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1),
    ))
    create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("2000"), period=BudgetPeriod.WEEKLY,
        start_date=datetime.date(2026, 6, 1),
    ))
    assert len(list_budgets(db_session)) == 2


def test_update_budget(db_session: Session):
    cat = _seed_cat(db_session, "Food")
    budget = create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("5000"), period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1),
    ))
    updated = update_budget(db_session, budget.id, BudgetUpdate(amount=Decimal("8000")))
    assert updated is not None
    assert updated.amount == Decimal("8000")


def test_update_nonexistent_budget(db_session: Session):
    result = update_budget(db_session, 999, BudgetUpdate(amount=Decimal("100")))
    assert result is None


def test_delete_budget(db_session: Session):
    cat = _seed_cat(db_session, "Food")
    budget = create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("5000"), period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1),
    ))
    ok, err = delete_budget(db_session, budget.id)
    assert ok is True
    assert err is None
    assert get_budget(db_session, budget.id) is None


def test_delete_nonexistent_budget(db_session: Session):
    ok, err = delete_budget(db_session, 999)
    assert ok is False
    assert err == "Budget not found"


# ------------------------------------------------------------------
# Budget progress
# ------------------------------------------------------------------


def test_budget_progress_no_data(db_session: Session):
    progress = budget_progress(db_session)
    assert progress == []


def test_budget_progress_with_spending(db_session: Session):
    from app.crud.account import create_account
    from app.models.account import AccountType
    from app.schemas.account import AccountCreate

    acct = create_account(db_session, AccountCreate(name="Bank", type=AccountType.BANK, opening_balance=Decimal("0")))
    cat = _seed_cat(db_session, "Food")
    budget = create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("10000"), period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1),
    ))

    # Spend 2500 on food
    create_transaction(db_session, acct.id, Decimal("-2500"), TransactionType.EXPENSE,
                       "Groceries", datetime.date(2026, 6, 5))

    # Update the budget's transaction to have category_id
    from app.crud.transaction import update_transaction
    update_transaction(db_session, 1, category_id=cat.id)

    progress = budget_progress(db_session, year=2026, month=6)
    assert len(progress) == 1
    p = progress[0]
    assert p["budget_id"] == budget.id
    assert p["category_name"] == "Food"
    assert p["spent"] == "2500.00"
    assert p["amount"] == "10000.00"
    assert p["percentage"] == 25.0
    assert p["remaining"] == "7500.00"
    assert p["over_budget"] is False


def test_budget_progress_over_budget(db_session: Session):
    from app.crud.account import create_account
    from app.models.account import AccountType
    from app.schemas.account import AccountCreate

    acct = create_account(db_session, AccountCreate(name="Bank", type=AccountType.BANK, opening_balance=Decimal("0")))
    cat = _seed_cat(db_session, "Food")
    create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("2000"), period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1),
    ))

    create_transaction(db_session, acct.id, Decimal("-2500"), TransactionType.EXPENSE,
                       "Groceries", datetime.date(2026, 6, 5))
    from app.crud.transaction import update_transaction
    update_transaction(db_session, 1, category_id=cat.id)

    progress = budget_progress(db_session, year=2026, month=6)
    assert len(progress) == 1
    p = progress[0]
    assert p["over_budget"] is True
    assert p["remaining"].startswith("-")


def test_budget_progress_ignores_inactive(db_session: Session):
    from app.crud.account import create_account
    from app.models.account import AccountType
    from app.schemas.account import AccountCreate

    acct = create_account(db_session, AccountCreate(name="Bank", type=AccountType.BANK, opening_balance=Decimal("0")))
    cat = _seed_cat(db_session, "Food")
    create_budget(db_session, BudgetCreate(
        category_id=cat.id, amount=Decimal("2000"), period=BudgetPeriod.MONTHLY,
        start_date=datetime.date(2026, 6, 1), is_active=False,
    ))

    create_transaction(db_session, acct.id, Decimal("-500"), TransactionType.EXPENSE,
                       "Groceries", datetime.date(2026, 6, 5))
    from app.crud.transaction import update_transaction
    update_transaction(db_session, 1, category_id=cat.id)

    progress = budget_progress(db_session, year=2026, month=6)
    assert len(progress) == 0


# ------------------------------------------------------------------
# HTTP — HTML pages
# ------------------------------------------------------------------


def test_budget_list_page(client: TestClient):
    response = client.get("/budgets")
    assert response.status_code == 200
    assert "Budgets" in response.text
    assert "Add budget" in response.text


def test_budget_new_page(client: TestClient):
    # Seed a category first
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    response = client.get("/budgets/new")
    assert response.status_code == 200
    assert "Create budget" in response.text
    assert "Food" in response.text


def test_budget_edit_page(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    client.post("/budgets", data={
        "category_id": "1", "amount": "5000", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    budgets = client.get("/api/budgets").json()
    budget_id = budgets[0]["id"]

    response = client.get(f"/budgets/{budget_id}/edit")
    assert response.status_code == 200
    assert "Save changes" in response.text


def test_budget_edit_page_not_found(client: TestClient):
    response = client.get("/budgets/99999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------
# HTTP — mutations
# ------------------------------------------------------------------


def test_create_budget_via_htmx(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    response = client.post("/budgets", data={
        "category_id": "1", "amount": "10000", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/budgets"


def test_update_budget_via_htmx(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    client.post("/budgets", data={
        "category_id": "1", "amount": "5000", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    response = client.patch("/budgets/1", data={"amount": "8000"},
                            headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/budgets"


def test_delete_budget_via_htmx(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    client.post("/budgets", data={
        "category_id": "1", "amount": "3000", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    budgets = client.get("/api/budgets").json()
    budget_id = budgets[0]["id"]

    response = client.delete(f"/budgets/{budget_id}",
                             headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "budget-deleted"


# ------------------------------------------------------------------
# HTTP — JSON API
# ------------------------------------------------------------------


def test_list_budgets_json(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    client.post("/budgets", data={
        "category_id": "1", "amount": "5000", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    response = client.get("/api/budgets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(b["amount"] == "5000.00" for b in data)


def test_get_budget_json(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    client.post("/budgets", data={
        "category_id": "1", "amount": "7500", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    budgets = client.get("/api/budgets").json()
    budget_id = budgets[0]["id"]

    response = client.get(f"/api/budgets/{budget_id}")
    assert response.status_code == 200
    assert response.json()["amount"] == "7500.00"


def test_get_budget_json_not_found(client: TestClient):
    response = client.get("/api/budgets/99999")
    assert response.status_code == 404


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def test_create_budget_zero_amount_fails(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    response = client.post("/budgets", data={
        "category_id": "1", "amount": "0", "period": "monthly",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


def test_create_budget_invalid_period_fails(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    response = client.post("/budgets", data={
        "category_id": "1", "amount": "1000", "period": "invalid",
        "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


# ------------------------------------------------------------------
# Dashboard budget endpoint
# ------------------------------------------------------------------


def test_dashboard_budgets_json(client: TestClient):
    response = client.get("/api/dashboard/budgets")
    assert response.status_code == 200
    data = response.json()
    assert "year" in data
    assert "month" in data
    assert "data" in data
