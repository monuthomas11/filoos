from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.account import create_account
from app.crud.category import create_category
from app.crud.recurring import (
    create_rule,
    delete_rule,
    get_rule,
    list_rules,
    update_last_generated_date,
    update_rule,
)
from app.models.account import AccountType
from app.models.recurring import RecurringFrequency
from app.schemas.account import AccountCreate
from app.schemas.category import CategoryCreate
from app.schemas.recurring import RecurringRuleCreate, RecurringRuleUpdate
from app.services.recurring import materialize_all, materialize_rule, next_occurrences


def _seed_account(db: Session, name: str = "Bank") -> int:
    return create_account(db, AccountCreate(name=name, type=AccountType.BANK, opening_balance=Decimal("0"))).id


def _seed_cat(db: Session, name: str = "Food") -> int:
    return create_category(db, CategoryCreate(name=name, type="expense", color="#16a34a")).id


def _make_rule_data(account_id: int, **overrides) -> RecurringRuleCreate:
    base = dict(
        account_id=account_id,
        amount=Decimal("50000"),
        type="income",
        description="Salary",
        frequency=RecurringFrequency.MONTHLY,
        interval=1,
        start_date=datetime.date(2026, 1, 1),
    )
    base.update(overrides)
    return RecurringRuleCreate(**base)


# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------


def test_recurring_frequency_enum():
    assert RecurringFrequency.DAILY.value == "daily"
    assert RecurringFrequency.WEEKLY.value == "weekly"
    assert RecurringFrequency.MONTHLY.value == "monthly"
    assert RecurringFrequency.YEARLY.value == "yearly"


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_create_and_read_rule(db_session: Session):
    acct_id = _seed_account(db_session)
    data = _make_rule_data(acct_id)
    rule = create_rule(db_session, data)
    assert rule.id is not None
    assert rule.account_id == acct_id
    assert rule.amount == Decimal("50000")
    assert rule.frequency == RecurringFrequency.MONTHLY

    fetched = get_rule(db_session, rule.id)
    assert fetched is not None
    assert fetched.description == "Salary"


def test_create_rule_with_category(db_session: Session):
    acct_id = _seed_account(db_session)
    cat_id = _seed_cat(db_session)
    data = _make_rule_data(acct_id, category_id=cat_id)
    rule = create_rule(db_session, data)
    assert rule.category_id == cat_id


def test_list_rules(db_session: Session):
    acct_id = _seed_account(db_session)
    create_rule(db_session, _make_rule_data(acct_id, description="Salary"))
    create_rule(db_session, _make_rule_data(acct_id, description="Rent", type="expense", amount=Decimal("20000")))
    assert len(list_rules(db_session)) == 2


def test_list_rules_active_only(db_session: Session):
    acct_id = _seed_account(db_session)
    create_rule(db_session, _make_rule_data(acct_id, description="Salary"))
    create_rule(db_session, _make_rule_data(acct_id, description="Old Rent", is_active=False))
    assert len(list_rules(db_session, active_only=True)) == 1


def test_update_rule(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(db_session, _make_rule_data(acct_id))
    updated = update_rule(db_session, rule.id, RecurringRuleUpdate(amount=Decimal("60000")))
    assert updated is not None
    assert updated.amount == Decimal("60000")


def test_update_nonexistent_rule(db_session: Session):
    result = update_rule(db_session, 999, RecurringRuleUpdate(amount=Decimal("100")))
    assert result is None


def test_delete_rule(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(db_session, _make_rule_data(acct_id))
    ok, err = delete_rule(db_session, rule.id)
    assert ok is True
    assert err is None
    assert get_rule(db_session, rule.id) is None


def test_delete_nonexistent_rule(db_session: Session):
    ok, err = delete_rule(db_session, 999)
    assert ok is False
    assert err == "Rule not found"


def test_update_last_generated_date(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(db_session, _make_rule_data(acct_id))
    d = datetime.date(2026, 6, 1)
    updated = update_last_generated_date(db_session, rule.id, d)
    assert updated is not None
    assert updated.last_generated_date == d


# ------------------------------------------------------------------
# Service — next_occurrences
# ------------------------------------------------------------------


def test_next_occurrences_monthly(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(db_session, _make_rule_data(acct_id, start_date=datetime.date(2026, 1, 1)))
    dates = next_occurrences(rule, count=3)
    assert len(dates) == 3
    assert dates[0] == datetime.date(2026, 2, 1)
    assert dates[1] == datetime.date(2026, 3, 1)
    assert dates[2] == datetime.date(2026, 4, 1)


def test_next_occurrences_monthly_day_of_month(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, start_date=datetime.date(2026, 1, 1), day_of_month=15),
    )
    dates = next_occurrences(rule, count=2)
    assert dates[0] == datetime.date(2026, 2, 15)
    assert dates[1] == datetime.date(2026, 3, 15)


def test_next_occurrences_weekly(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, frequency=RecurringFrequency.WEEKLY, start_date=datetime.date(2026, 6, 1), day_of_week=0),
    )
    dates = next_occurrences(rule, count=3)
    assert len(dates) == 3
    # June 1 2026 is a Monday (0), next Monday is June 8
    assert dates[0] == datetime.date(2026, 6, 8)
    assert dates[1] == datetime.date(2026, 6, 15)
    assert dates[2] == datetime.date(2026, 6, 22)


def test_next_occurrences_daily(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, frequency=RecurringFrequency.DAILY, start_date=datetime.date(2026, 6, 1)),
    )
    dates = next_occurrences(rule, count=3)
    assert dates[0] == datetime.date(2026, 6, 2)
    assert dates[1] == datetime.date(2026, 6, 3)
    assert dates[2] == datetime.date(2026, 6, 4)


def test_next_occurrences_yearly(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, frequency=RecurringFrequency.YEARLY, start_date=datetime.date(2026, 1, 1)),
    )
    dates = next_occurrences(rule, count=2)
    assert dates[0] == datetime.date(2027, 1, 1)
    assert dates[1] == datetime.date(2028, 1, 1)


def test_next_occurrences_respects_end_date(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 3, 15)),
    )
    dates = next_occurrences(rule, count=10)
    assert len(dates) == 2  # Feb 1, March 1
    assert dates[0] == datetime.date(2026, 2, 1)
    assert dates[1] == datetime.date(2026, 3, 1)


def test_next_occurrences_from_last_generated(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(db_session, _make_rule_data(acct_id, start_date=datetime.date(2026, 1, 1)))
    update_last_generated_date(db_session, rule.id, datetime.date(2026, 4, 1))
    rule = get_rule(db_session, rule.id)
    dates = next_occurrences(rule, count=2)
    assert dates[0] == datetime.date(2026, 5, 1)
    assert dates[1] == datetime.date(2026, 6, 1)


# ------------------------------------------------------------------
# Service — materialize_rule
# ------------------------------------------------------------------


def test_materialize_rule_creates_transactions(db_session: Session):
    from app.crud.transaction import list_transactions

    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, frequency=RecurringFrequency.DAILY, amount=Decimal("1000"), type="expense",
                        description="Daily coffee", start_date=datetime.date(2026, 6, 1)),
    )

    # Manually override last_generated_date to limit the range
    update_last_generated_date(db_session, rule.id, datetime.date(2026, 5, 31))
    rule = get_rule(db_session, rule.id)

    # Only 3 days of materialization (June 1-3 relative to May 31)
    count = materialize_rule(db_session, rule)
    assert count >= 1

    txs = list_transactions(db_session)
    assert len(txs) == count
    for tx in txs:
        assert tx.description == "Daily coffee"
        assert tx.amount == Decimal("-1000")


def test_materialize_rule_idempotent(db_session: Session):
    acct_id = _seed_account(db_session)
    rule = create_rule(
        db_session,
        _make_rule_data(acct_id, frequency=RecurringFrequency.DAILY, amount=Decimal("500"), type="expense",
                        description="Snacks", start_date=datetime.date(2026, 6, 1)),
    )
    update_last_generated_date(db_session, rule.id, datetime.date(2026, 5, 31))
    rule = get_rule(db_session, rule.id)

    count1 = materialize_rule(db_session, rule)

    # Second call should produce 0 new transactions
    count2 = materialize_rule(db_session, rule)
    assert count2 == 0

    from app.crud.transaction import list_transactions
    assert len(list_transactions(db_session)) == count1


def test_materialize_all(db_session: Session):
    from app.crud.transaction import list_transactions

    acct_id = _seed_account(db_session)
    r1 = create_rule(
        db_session,
        _make_rule_data(acct_id, description="Daily coffee", type="expense", amount=Decimal("500"),
                        frequency=RecurringFrequency.DAILY, start_date=datetime.date(2026, 6, 1)),
    )
    r2 = create_rule(
        db_session,
        _make_rule_data(acct_id, description="Daily snack", type="expense", amount=Decimal("300"),
                        frequency=RecurringFrequency.DAILY, start_date=datetime.date(2026, 6, 1)),
    )
    update_last_generated_date(db_session, r1.id, datetime.date(2026, 5, 31))
    update_last_generated_date(db_session, r2.id, datetime.date(2026, 5, 31))

    results = materialize_all(db_session)
    assert len(results) == 2
    total = sum(results.values())
    assert total >= 2
    assert len(list_transactions(db_session)) == total


def test_materialize_all_skips_inactive(db_session: Session):
    acct_id = _seed_account(db_session)
    r1 = create_rule(
        db_session,
        _make_rule_data(acct_id, description="Active", start_date=datetime.date(2026, 6, 1), is_active=True),
    )
    r2 = create_rule(
        db_session,
        _make_rule_data(acct_id, description="Inactive", start_date=datetime.date(2026, 6, 1), is_active=False),
    )
    update_last_generated_date(db_session, r1.id, datetime.date(2026, 5, 31))
    update_last_generated_date(db_session, r2.id, datetime.date(2026, 5, 31))

    results = materialize_all(db_session)
    assert r1.id in results
    assert r2.id not in results


# ------------------------------------------------------------------
# HTTP — HTML pages
# ------------------------------------------------------------------


def test_recurring_list_page(client: TestClient):
    response = client.get("/recurring")
    assert response.status_code == 200
    assert "Recurring Rules" in response.text
    assert "Add rule" in response.text


def test_recurring_new_page(client: TestClient):
    # Seed an account first
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    response = client.get("/recurring/new")
    assert response.status_code == 200
    assert "New recurring rule" in response.text
    assert "Bank" in response.text


def test_recurring_edit_page(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]

    response = client.get(f"/recurring/{rule_id}/edit")
    assert response.status_code == 200
    assert "Save changes" in response.text


def test_recurring_edit_page_not_found(client: TestClient):
    response = client.get("/recurring/99999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------
# HTTP — mutations
# ------------------------------------------------------------------


def test_create_rule_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    response = client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/recurring"


def test_update_rule_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    response = client.patch("/recurring/1", data={"amount": "60000"},
                            headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/recurring"


def test_delete_rule_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]

    response = client.delete(f"/recurring/{rule_id}",
                             headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "recurring-rule-deleted"


# ------------------------------------------------------------------
# HTTP — JSON API
# ------------------------------------------------------------------


def test_list_rules_json(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    response = client.get("/api/recurring")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(r["amount"] == "50000.00" for r in data)


def test_get_rule_json(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]

    response = client.get(f"/api/recurring/{rule_id}")
    assert response.status_code == 200
    assert response.json()["description"] == "Salary"


def test_get_rule_json_not_found(client: TestClient):
    response = client.get("/api/recurring/99999")
    assert response.status_code == 404


# ------------------------------------------------------------------
# HTTP — Preview and materialize endpoints
# ------------------------------------------------------------------


def test_preview_endpoint(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "50000", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]

    response = client.get(f"/api/recurring/{rule_id}/preview")
    assert response.status_code == 200
    data = response.json()
    assert data["rule_id"] == rule_id
    assert len(data["next_dates"]) > 0


def test_materialize_endpoint(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    client.post("/recurring", data={
        "account_id": "1", "amount": "1000", "type": "expense", "description": "Daily coffee",
        "frequency": "daily", "start_date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]

    # Set last_generated_date so materialize produces some transactions
    client.patch(f"/recurring/{rule_id}", data={"last_generated_date": "2026-05-31"},
                 headers={"HX-Request": "true"})

    response = client.post("/api/recurring/materialize")
    assert response.status_code == 200
    data = response.json()
    assert "total_materialized" in data
    assert data["total_materialized"] >= 1


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def test_create_rule_zero_amount_fails(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    response = client.post("/recurring", data={
        "account_id": "1", "amount": "0", "type": "income", "description": "Salary",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


def test_create_rule_invalid_type_fails(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    response = client.post("/recurring", data={
        "account_id": "1", "amount": "5000", "type": "invalid", "description": "Test",
        "frequency": "monthly", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


def test_create_rule_invalid_frequency_fails(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank", "opening_balance": "0", "currency": "INR"},
                headers={"HX-Request": "true"})
    response = client.post("/recurring", data={
        "account_id": "1", "amount": "5000", "type": "expense", "description": "Test",
        "frequency": "invalid", "start_date": "2026-01-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422
