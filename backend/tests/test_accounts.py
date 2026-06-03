"""Tests for the Account model, CRUD, and HTTP endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.account import (
    compute_balance,
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from app.models.account import AccountType
from app.schemas.account import AccountCreate, AccountUpdate

# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------


def test_account_enum_values():
    """AccountType enum values match what the UI expects."""
    assert AccountType.CASH.value == "cash"
    assert AccountType.BANK.value == "bank"
    assert AccountType.CREDIT_CARD.value == "credit_card"
    assert AccountType.SAVINGS.value == "savings"
    assert AccountType.INVESTMENT.value == "investment"


def test_account_default_color_by_type(db_session: Session):
    """Creating without a colour infers one from the type."""
    data = AccountCreate(name="Cash Wallet", type=AccountType.CASH)
    account = create_account(db_session, data)
    # Cash defaults to green (#16a34a)
    assert account.color == "#16a34a"


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_create_and_read_account(db_session: Session):
    data = AccountCreate(
        name="HDFC Savings",
        type=AccountType.BANK,
        currency="INR",
        opening_balance=Decimal("5000.00"),
        color="#4f46e5",
    )
    account = create_account(db_session, data)
    assert account.id is not None
    assert account.name == "HDFC Savings"
    assert account.type == AccountType.BANK
    assert account.opening_balance == Decimal("5000.00")
    assert account.currency == "INR"
    assert account.is_active is True

    fetched = get_account(db_session, account.id)
    assert fetched is not None
    assert fetched.name == "HDFC Savings"


def test_list_accounts(db_session: Session):
    create_account(db_session, AccountCreate(name="A", type=AccountType.CASH))
    create_account(db_session, AccountCreate(name="B", type=AccountType.BANK))
    assert len(list_accounts(db_session)) == 2


def test_update_account(db_session: Session):
    account = create_account(db_session, AccountCreate(name="Old Name", type=AccountType.CASH))
    updated = update_account(
        db_session, account.id, AccountUpdate(name="New Name", is_active=False)
    )
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.is_active is False


def test_update_nonexistent_account(db_session: Session):
    result = update_account(db_session, 999, AccountUpdate(name="Nope"))
    assert result is None


def test_delete_account(db_session: Session):
    account = create_account(db_session, AccountCreate(name="Delete Me", type=AccountType.CASH))
    assert delete_account(db_session, account.id) is True
    assert get_account(db_session, account.id) is None


def test_delete_nonexistent_account(db_session: Session):
    assert delete_account(db_session, 999) is False


def test_compute_balance_defaults_to_opening(db_session: Session):
    """Until Phase 3, balance equals the opening balance."""
    data = AccountCreate(name="Test", type=AccountType.SAVINGS, opening_balance=Decimal("10000"))
    account = create_account(db_session, data)
    assert compute_balance(account, db_session) == Decimal("10000")


# ------------------------------------------------------------------
# HTTP — HTML pages
# ------------------------------------------------------------------


def test_account_list_page(client: TestClient):
    # Seed via the API itself (avoids sharing in-memory session across threads).
    client.post("/accounts", data={"name": "Seeded", "type": "bank"}, headers={"HX-Request": "true"})
    response = client.get("/accounts")
    assert response.status_code == 200
    assert "Seeded" in response.text


def test_account_new_page(client: TestClient):
    response = client.get("/accounts/new")
    assert response.status_code == 200
    assert "Create account" in response.text


def test_account_edit_page(client: TestClient):
    # Create via API first.
    client.post("/accounts", data={"name": "Edit Me", "type": "credit_card"}, headers={"HX-Request": "true"})
    # Find the account via the JSON API.
    accounts = client.get("/api/accounts").json()
    account_id = accounts[0]["id"]

    response = client.get(f"/accounts/{account_id}/edit")
    assert response.status_code == 200
    assert "Edit Me" in response.text
    assert "Save changes" in response.text


def test_account_edit_page_not_found(client: TestClient):
    response = client.get("/accounts/99999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------
# HTTP — mutations (via form data simulating HTMX)
# ------------------------------------------------------------------


def test_create_account_via_htmx(client: TestClient):
    response = client.post(
        "/accounts",
        data={
            "name": "HTMX Cash",
            "type": "cash",
            "currency": "INR",
            "opening_balance": "1000",
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/accounts"


def test_update_account_via_htmx(client: TestClient):
    # Create first.
    r = client.post("/accounts", data={"name": "Before", "type": "bank"}, headers={"HX-Request": "true"})
    assert r.headers.get("HX-Redirect") == "/accounts"

    response = client.patch(
        "/accounts/1",
        data={"name": "After"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/accounts"


def test_delete_account_via_htmx(client: TestClient):
    # Create first.
    client.post("/accounts", data={"name": "Delete Me", "type": "cash"}, headers={"HX-Request": "true"})
    accounts = client.get("/api/accounts").json()
    account_id = accounts[0]["id"]

    response = client.delete(
        f"/accounts/{account_id}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "account-deleted"


# ------------------------------------------------------------------
# HTTP — JSON API
# ------------------------------------------------------------------


def test_list_accounts_json(client: TestClient):
    client.post("/accounts", data={"name": "JSON Acct", "type": "savings"}, headers={"HX-Request": "true"})
    response = client.get("/api/accounts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(a["name"] == "JSON Acct" for a in data)


def test_get_account_json(client: TestClient):
    client.post("/accounts", data={"name": "Single", "type": "investment"}, headers={"HX-Request": "true"})
    accounts = client.get("/api/accounts").json()
    account_id = accounts[0]["id"]

    response = client.get(f"/api/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Single"


def test_get_account_json_not_found(client: TestClient):
    response = client.get("/api/accounts/99999")
    assert response.status_code == 404


def test_balance_json(client: TestClient):
    client.post(
        "/accounts",
        data={"name": "Bal", "type": "cash", "opening_balance": "2500"},
        headers={"HX-Request": "true"},
    )
    # Find the account via the JSON API.
    accounts = client.get("/api/accounts").json()
    account_id = accounts[0]["id"]

    response = client.get(f"/api/accounts/{account_id}/balance")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["balance"]) == Decimal("2500")


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def test_create_account_empty_name_fails(client: TestClient):
    response = client.post(
        "/accounts",
        data={"name": "", "type": "cash"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 422


def test_create_account_invalid_type_fails(client: TestClient):
    response = client.post(
        "/accounts",
        data={"name": "Bad Type", "type": "invalid"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 422
