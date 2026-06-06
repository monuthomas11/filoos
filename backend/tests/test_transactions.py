"""Tests for the Transaction model, CRUD, and HTTP endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.account import create_account
from app.crud.transaction import (
    compute_account_balance,
    create_transaction,
    create_transfer,
    delete_transaction,
    delete_transfer_pair,
    get_recent_transactions,
    get_transaction,
    list_transactions,
    update_transaction,
    update_transfer_pair,
)
from app.models.account import Account, AccountType
from app.models.transaction import TransactionType
from app.schemas.account import AccountCreate


def _seed_account(db: Session, name: str = "Test Account",
                  type_: AccountType = AccountType.BANK,
                  balance: str = "0") -> Account:
    return create_account(
        db,
        AccountCreate(name=name, type=type_, opening_balance=Decimal(balance)),
    )


# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------


def test_transaction_type_enum_values():
    assert TransactionType.EXPENSE.value == "expense"
    assert TransactionType.INCOME.value == "income"
    assert TransactionType.TRANSFER.value == "transfer"


def test_create_and_read_transaction(db_session: Session):
    acct = _seed_account(db_session, "Test", balance="1000")
    tx = create_transaction(
        db=db_session,
        account_id=acct.id,
        amount=Decimal("-250.00"),
        type_=TransactionType.EXPENSE,
        description="Grocery run",
        date=datetime.date(2026, 6, 1),
        notes="Weekly groceries",
    )
    assert tx.id is not None
    assert tx.account_id == acct.id
    assert tx.amount == Decimal("-250.00")
    assert tx.type == TransactionType.EXPENSE
    assert tx.description == "Grocery run"
    assert tx.notes == "Weekly groceries"
    assert tx.date == datetime.date(2026, 6, 1)
    assert tx.transfer_pair_id is None
    assert tx.recurring_rule_id is None

    fetched = get_transaction(db_session, tx.id)
    assert fetched is not None
    assert fetched.description == "Grocery run"


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_list_transactions_empty(db_session: Session):
    assert list_transactions(db_session) == []


def test_list_transactions_with_filters(db_session: Session):
    acct1 = _seed_account(db_session, "A", balance="1000")
    acct2 = _seed_account(db_session, "B", balance="2000")

    create_transaction(db_session, acct1.id, Decimal("-50"), TransactionType.EXPENSE,
                       "Coffee", datetime.date(2026, 6, 1))
    create_transaction(db_session, acct1.id, Decimal("200"), TransactionType.INCOME,
                       "Freelance", datetime.date(2026, 6, 2))
    create_transaction(db_session, acct2.id, Decimal("-30"), TransactionType.EXPENSE,
                       "Snacks", datetime.date(2026, 6, 1))

    assert len(list_transactions(db_session)) == 3
    assert len(list_transactions(db_session, account_id=acct1.id)) == 2
    assert len(list_transactions(db_session, type_filter=TransactionType.INCOME)) == 1
    assert len(list_transactions(
        db_session, date_from=datetime.date(2026, 6, 2))) == 1
    assert len(list_transactions(
        db_session, date_to=datetime.date(2026, 6, 1))) == 2
    assert len(list_transactions(db_session, description="coffee")) == 1


def test_update_transaction(db_session: Session):
    acct = _seed_account(db_session, "Test")
    tx = create_transaction(db_session, acct.id, Decimal("-100"),
                            TransactionType.EXPENSE, "Old", datetime.date.today())
    updated = update_transaction(db_session, tx.id, description="New")
    assert updated is not None
    assert updated.description == "New"


def test_update_nonexistent_transaction(db_session: Session):
    result = update_transaction(db_session, 999, description="Nope")
    assert result is None


def test_delete_transaction(db_session: Session):
    acct = _seed_account(db_session, "Test")
    tx = create_transaction(db_session, acct.id, Decimal("-50"),
                            TransactionType.EXPENSE, "Delete Me", datetime.date.today())
    assert delete_transaction(db_session, tx.id) is True
    assert get_transaction(db_session, tx.id) is None


def test_delete_nonexistent_transaction(db_session: Session):
    assert delete_transaction(db_session, 999) is False


# ------------------------------------------------------------------
# Balance computation
# ------------------------------------------------------------------


def test_compute_account_balance(db_session: Session):
    acct = _seed_account(db_session, "Test", balance="1000")
    # opening is 1000, add an expense and income
    create_transaction(db_session, acct.id, Decimal("-200"),
                       TransactionType.EXPENSE, "Spend", datetime.date(2026, 6, 1))
    create_transaction(db_session, acct.id, Decimal("500"),
                       TransactionType.INCOME, "Earn", datetime.date(2026, 6, 2))
    assert compute_account_balance(acct, db_session) == Decimal("1300")


def test_compute_account_balance_edge(db_session: Session):
    acct = _seed_account(db_session, "Test", balance="0")
    assert compute_account_balance(acct, db_session) == Decimal("0")


# ------------------------------------------------------------------
# Transfers
# ------------------------------------------------------------------


def test_create_transfer(db_session: Session):
    from_acct = _seed_account(db_session, "Source", balance="5000")
    to_acct = _seed_account(db_session, "Dest", balance="1000")

    out_tx, in_tx = create_transfer(
        db=db_session,
        from_account_id=from_acct.id,
        to_account_id=to_acct.id,
        amount=Decimal("1000"),
        description="Transfer",
        date=datetime.date(2026, 6, 1),
    )

    assert out_tx.amount == Decimal("-1000")
    assert out_tx.type == TransactionType.TRANSFER
    assert out_tx.account_id == from_acct.id
    assert out_tx.transfer_pair_id == in_tx.id

    assert in_tx.amount == Decimal("1000")
    assert in_tx.type == TransactionType.TRANSFER
    assert in_tx.account_id == to_acct.id
    assert in_tx.transfer_pair_id == out_tx.id

    # Balances updated correctly
    assert compute_account_balance(from_acct, db_session) == Decimal("4000")
    assert compute_account_balance(to_acct, db_session) == Decimal("2000")


# ------------------------------------------------------------------
# Recent transactions
# ------------------------------------------------------------------


def test_get_recent_transactions(db_session: Session):
    acct = _seed_account(db_session, "Test")
    for i in range(15):
        create_transaction(db_session, acct.id, Decimal(f"-{i+1}"),
                           TransactionType.EXPENSE, f"Txn {i}",
                           datetime.date(2026, 6, min(i + 1, 30)))
    recent = get_recent_transactions(db_session, limit=10)
    assert len(recent) == 10
    # Most recent first
    assert recent[0].description == "Txn 14"


# ------------------------------------------------------------------
# HTTP — HTML pages
# ------------------------------------------------------------------


def test_transaction_list_page(client: TestClient):
    response = client.get("/transactions")
    assert response.status_code == 200
    assert "Transactions" in response.text
    assert "Add transaction" in response.text


def test_transaction_new_page(client: TestClient):
    # Seed an account first
    client.post("/accounts", data={"name": "My Account", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.get("/transactions/new")
    assert response.status_code == 200
    assert "New transaction" in response.text
    assert "My Account" in response.text


def test_transaction_edit_page(client: TestClient):
    # Seed
    client.post("/accounts", data={"name": "Acct", "type": "cash"},
                headers={"HX-Request": "true"})
    # Create a transaction
    client.post("/transactions", data={
        "type": "expense",
        "account_id": "1",
        "amount": "100",
        "description": "Edit Me",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    # Find it via the JSON API.
    txs = client.get("/api/transactions").json()
    tx_id = txs[0]["id"]

    response = client.get(f"/transactions/{tx_id}/edit")
    assert response.status_code == 200
    assert "Edit Me" in response.text
    assert "Save changes" in response.text


def test_transaction_edit_page_not_found(client: TestClient):
    response = client.get("/transactions/99999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------
# HTTP — mutations (via form data simulating HTMX)
# ------------------------------------------------------------------


def test_create_expense_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Wallet", "type": "cash"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "expense",
        "account_id": "1",
        "amount": "75.50",
        "description": "Lunch",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/transactions"


def test_create_income_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Bank", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "income",
        "account_id": "1",
        "amount": "5000",
        "description": "Salary",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/transactions"


def test_create_transfer_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Savings", "type": "savings"},
                headers={"HX-Request": "true"})
    client.post("/accounts", data={"name": "Checking", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "transfer",
        "from_account_id": "1",
        "to_account_id": "2",
        "amount": "2000",
        "description": "Move money",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/transactions"


def test_update_transaction_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "cash"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "expense", "account_id": "1", "amount": "50",
        "description": "Before", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    txs = client.get("/api/transactions").json()
    tx_id = txs[0]["id"]

    response = client.patch(f"/transactions/{tx_id}", data={
        "description": "After",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/transactions"


def test_delete_transaction_via_htmx(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "cash"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "expense", "account_id": "1", "amount": "25",
        "description": "Delete Me", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    txs = client.get("/api/transactions").json()
    tx_id = txs[0]["id"]

    response = client.delete(f"/transactions/{tx_id}",
                             headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "transaction-deleted"


# ------------------------------------------------------------------
# HTTP — JSON API
# ------------------------------------------------------------------


def test_list_transactions_json(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "expense", "account_id": "1", "amount": "30",
        "description": "Bus fare", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    response = client.get("/api/transactions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(t["description"] == "Bus fare" for t in data)


def test_get_transaction_json(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "income", "account_id": "1", "amount": "999",
        "description": "Bonus", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    # Find the transaction via the JSON API.
    txs = client.get("/api/transactions").json()
    tx_id = txs[0]["id"]

    response = client.get(f"/api/transactions/{tx_id}")
    assert response.status_code == 200
    assert response.json()["description"] == "Bonus"


def test_get_transaction_json_not_found(client: TestClient):
    response = client.get("/api/transactions/99999")
    assert response.status_code == 404


# ------------------------------------------------------------------
# Dashboard shows recent transactions
# ------------------------------------------------------------------


def test_dashboard_shows_recent_transactions(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "expense", "account_id": "1", "amount": "42",
        "description": "Dashboard test", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    response = client.get("/")
    assert response.status_code == 200
    assert "Dashboard test" in response.text


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def test_create_transaction_empty_description_fails(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "expense", "account_id": "1", "amount": "10",
        "description": "", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


def test_create_transaction_invalid_type_fails(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "invalid", "account_id": "1", "amount": "10",
        "description": "Bad", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


def test_create_transaction_zero_amount_fails(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "expense", "account_id": "1", "amount": "0",
        "description": "Free", "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


def test_transfer_same_account_fails(client: TestClient):
    client.post("/accounts", data={"name": "Acct", "type": "bank"},
                headers={"HX-Request": "true"})
    response = client.post("/transactions", data={
        "type": "transfer",
        "from_account_id": "1",
        "to_account_id": "1",
        "amount": "100",
        "description": "Self transfer",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})
    assert response.status_code == 422


# ------------------------------------------------------------------
# P1 — Transfer pair safety
# ------------------------------------------------------------------


def test_delete_transfer_both_legs(db_session: Session):
    """Deleting a transfer should delete both legs."""
    from_acct = _seed_account(db_session, "Source", balance="5000")
    to_acct = _seed_account(db_session, "Dest", balance="1000")

    out_tx, in_tx = create_transfer(
        db=db_session,
        from_account_id=from_acct.id,
        to_account_id=to_acct.id,
        amount=Decimal("1000"),
        description="Transfer",
        date=datetime.date(2026, 6, 1),
    )

    ok = delete_transfer_pair(db_session, out_tx.id)
    assert ok is True
    assert get_transaction(db_session, out_tx.id) is None
    assert get_transaction(db_session, in_tx.id) is None


def test_delete_transfer_from_incoming_leg(db_session: Session):
    """Deleting the incoming leg should also delete the outgoing leg."""
    from_acct = _seed_account(db_session, "Source", balance="5000")
    to_acct = _seed_account(db_session, "Dest", balance="1000")

    out_tx, in_tx = create_transfer(
        db=db_session,
        from_account_id=from_acct.id,
        to_account_id=to_acct.id,
        amount=Decimal("1000"),
        description="Transfer",
        date=datetime.date(2026, 6, 1),
    )

    ok = delete_transfer_pair(db_session, in_tx.id)
    assert ok is True
    assert get_transaction(db_session, out_tx.id) is None
    assert get_transaction(db_session, in_tx.id) is None


def test_delete_transfer_pair_nonexistent(db_session: Session):
    assert delete_transfer_pair(db_session, 999) is False


def test_update_transfer_pair(db_session: Session):
    """Updating a transfer should update both legs atomically."""
    from_acct = _seed_account(db_session, "Source", balance="5000")
    to_acct = _seed_account(db_session, "Dest", balance="1000")

    out_tx, in_tx = create_transfer(
        db=db_session,
        from_account_id=from_acct.id,
        to_account_id=to_acct.id,
        amount=Decimal("1000"),
        description="Transfer",
        date=datetime.date(2026, 6, 1),
    )

    result = update_transfer_pair(
        db_session,
        out_tx.id,
        amount=Decimal("2000"),
        description="Updated Transfer",
        date=datetime.date(2026, 6, 15),
    )

    assert result is not None
    updated_out, updated_in = result

    # Outgoing leg should be negative
    assert updated_out.amount == Decimal("-2000")
    assert updated_out.description == "Updated Transfer"
    assert updated_out.date == datetime.date(2026, 6, 15)
    assert updated_out.account_id == from_acct.id

    # Incoming leg should be positive
    assert updated_in.amount == Decimal("2000")
    assert updated_in.description == "Updated Transfer"
    assert updated_in.date == datetime.date(2026, 6, 15)
    assert updated_in.account_id == to_acct.id

    # Balances should reflect the new amount
    assert compute_account_balance(from_acct, db_session) == Decimal("3000")
    assert compute_account_balance(to_acct, db_session) == Decimal("3000")


def test_update_transfer_pair_swap_accounts(db_session: Session):
    """Swapping from/to accounts should reassign the legs correctly."""
    from_acct = _seed_account(db_session, "Source", balance="5000")
    to_acct = _seed_account(db_session, "Dest", balance="1000")

    out_tx, in_tx = create_transfer(
        db=db_session,
        from_account_id=from_acct.id,
        to_account_id=to_acct.id,
        amount=Decimal("1000"),
        description="Transfer",
        date=datetime.date(2026, 6, 1),
    )

    # Swap accounts
    result = update_transfer_pair(
        db_session,
        out_tx.id,
        from_account_id=to_acct.id,
        to_account_id=from_acct.id,
    )

    assert result is not None
    updated_out, updated_in = result

    # Outgoing leg is now from to_acct
    assert updated_out.account_id == to_acct.id
    assert updated_out.amount == Decimal("-1000")

    # Incoming leg is now to from_acct
    assert updated_in.account_id == from_acct.id
    assert updated_in.amount == Decimal("1000")

    # Balances should reflect the swap
    assert compute_account_balance(from_acct, db_session) == Decimal("6000")
    assert compute_account_balance(to_acct, db_session) == Decimal("0")


def test_update_transfer_pair_nonexistent(db_session: Session):
    result = update_transfer_pair(db_session, 999, description="Nope")
    assert result is None


def test_edit_transfer_page_returns_200(client: TestClient):
    """GET /transactions/{id}/edit for a transfer should return 200."""
    client.post("/accounts", data={"name": "Source", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/accounts", data={"name": "Dest", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "transfer",
        "from_account_id": "1",
        "to_account_id": "2",
        "amount": "500",
        "description": "Transfer",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})

    txs = client.get("/api/transactions").json()
    transfer_tx = next(t for t in txs if t["type"] == "transfer")

    response = client.get(f"/transactions/{transfer_tx['id']}/edit")
    assert response.status_code == 200
    assert "Transfer" in response.text
    assert "Save changes" in response.text


def test_edit_transfer_via_htmx(client: TestClient):
    """PATCH /transactions/{id} for a transfer should update both legs."""
    client.post("/accounts", data={"name": "Source", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/accounts", data={"name": "Dest", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "transfer",
        "from_account_id": "1",
        "to_account_id": "2",
        "amount": "500",
        "description": "Transfer",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})

    txs = client.get("/api/transactions").json()
    transfer_tx = next(t for t in txs if t["type"] == "transfer")

    response = client.patch(
        f"/transactions/{transfer_tx['id']}",
        data={
            "amount": "1000",
            "description": "Updated Transfer",
            "date": "2026-06-15",
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/transactions"

    # Verify both legs were updated
    txs = client.get("/api/transactions").json()
    assert len(txs) == 2
    amounts = sorted([t["amount"] for t in txs])
    assert amounts == ["-1000.00", "1000.00"]
    assert all(t["description"] == "Updated Transfer" for t in txs)


def test_edit_transfer_via_json(client: TestClient):
    """PATCH /transactions/{id} for a transfer (form data) should update both legs."""
    client.post("/accounts", data={"name": "Source", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/accounts", data={"name": "Dest", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "transfer",
        "from_account_id": "1",
        "to_account_id": "2",
        "amount": "500",
        "description": "Transfer",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})

    txs = client.get("/api/transactions").json()
    transfer_tx = next(t for t in txs if t["type"] == "transfer")

    response = client.patch(
        f"/transactions/{transfer_tx['id']}",
        data={"amount": "750", "description": "JSON Update", "date": "2026-06-20"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "JSON Update"


def test_delete_transfer_via_htmx(client: TestClient):
    """Deleting a transfer via HTMX should delete both legs."""
    client.post("/accounts", data={"name": "Source", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/accounts", data={"name": "Dest", "type": "bank"},
                headers={"HX-Request": "true"})
    client.post("/transactions", data={
        "type": "transfer",
        "from_account_id": "1",
        "to_account_id": "2",
        "amount": "500",
        "description": "Transfer",
        "date": "2026-06-01",
    }, headers={"HX-Request": "true"})

    txs = client.get("/api/transactions").json()
    transfer_tx = next(t for t in txs if t["type"] == "transfer")

    response = client.delete(
        f"/transactions/{transfer_tx['id']}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "transaction-deleted"

    # Verify both legs are deleted
    remaining = client.get("/api/transactions").json()
    assert len(remaining) == 0


# ------------------------------------------------------------------
# Quick-add redirect (Phase 4.1) — dashboard CTA + next-param threading
# ------------------------------------------------------------------


def test_dashboard_has_add_transaction_button(client: TestClient):
    """The dashboard must contain a primary CTA linking to /transactions/new."""
    r = client.get("/")
    assert r.status_code == 200
    assert "/transactions/new" in r.text
    assert "Add transaction" in r.text


def test_dashboard_button_passes_from_query_param(client: TestClient):
    """The dashboard CTA must include ?from=/ so the form knows the entry point."""
    r = client.get("/")
    assert r.status_code == 200
    # Find the link to the create form and verify it carries ?from=/
    assert 'href="/transactions/new?from=/"' in r.text


def test_create_form_renders_next_hidden_input(client: TestClient):
    """GET /transactions/new?from=/ must render a hidden next input set to '/'."""
    r = client.get("/transactions/new", params={"from": "/"})
    assert r.status_code == 200
    assert 'name="next" value="/"' in r.text


def test_create_form_default_next_is_transactions(client: TestClient):
    """GET /transactions/new (no from param) must default next to /transactions."""
    r = client.get("/transactions/new")
    assert r.status_code == 200
    assert 'name="next" value="/transactions"' in r.text


def test_create_via_htmx_with_next_returns_custom_redirect(client: TestClient, db_session: Session):
    """POST /transactions with next=/ and a valid payload must return HX-Redirect: /."""
    acc = _seed_account(db_session, "Test Account", AccountType.CASH, "0")
    db_session.commit()

    r = client.post(
        "/transactions",
        data={
            "type": "expense",
            "account_id": str(acc.id),
            "amount": "10.00",
            "description": "Coffee",
            "date": "2026-06-05",
            "next": "/",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers.get("HX-Redirect") == "/"


def test_create_via_htmx_without_next_falls_back_to_transactions(client: TestClient, db_session: Session):
    """POST /transactions with no next field must fall back to HX-Redirect: /transactions."""
    acc = _seed_account(db_session, "Test Account 2", AccountType.CASH, "0")
    db_session.commit()

    r = client.post(
        "/transactions",
        data={
            "type": "expense",
            "account_id": str(acc.id),
            "amount": "5.00",
            "description": "Tea",
            "date": "2026-06-05",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers.get("HX-Redirect") == "/transactions"


def test_create_via_htmx_rejects_unsafe_next(client: TestClient, db_session: Session):
    """POST /transactions with a non-local next value must fall back to /transactions."""
    acc = _seed_account(db_session, "Test Account 3", AccountType.CASH, "0")
    db_session.commit()

    for bad in ("//evil.com/x", "http://evil.com", "javascript:alert(1)"):
        r = client.post(
            "/transactions",
            data={
                "type": "expense",
                "account_id": str(acc.id),
                "amount": "1.00",
                "description": "X",
                "date": "2026-06-05",
                "next": bad,
            },
            headers={"HX-Request": "true"},
        )
        assert r.status_code == 200, f"Bad next={bad!r} returned {r.status_code}"
        assert r.headers.get("HX-Redirect") == "/transactions", (
            f"Bad next={bad!r} should fall back to /transactions"
        )


def test_cancel_link_follows_next(client: TestClient):
    """The Cancel link on the create form must point to next_url when provided."""
    r = client.get("/transactions/new", params={"from": "/"})
    assert r.status_code == 200
    # The Cancel link should be '/' when next is '/'
    assert 'href="/"' in r.text
