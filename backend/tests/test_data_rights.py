"""Tests for P1 data subject rights — delete account, data export, last_login_at."""

from __future__ import annotations

import datetime as dt
from datetime import UTC

from app.config import get_settings
from app.crud.user import delete_user_by_id, get_all_user_data
from app.models.account import Account
from app.models.budget import Budget, BudgetPeriod
from app.models.category import Category, CategoryType
from app.models.recurring import RecurringFrequency, RecurringRule, RecurringTransactionType
from app.models.transaction import Transaction, TransactionType
from app.models.user import User

# ── P1.4 — last_login_at is set on login ──────────────────────────


def test_last_login_at_set_on_callback(anon_client, _db):
    """P1.4: After OAuth callback, user.last_login_at should be set (not None)."""
    from tests.conftest import _login

    before = dt.datetime.now(UTC).replace(tzinfo=None)
    _login(anon_client, {"email": "u@g.com", "sub": "sub-ll", "name": "U"})
    _, Sess = _db
    with Sess() as db:
        user = db.query(User).filter_by(google_sub="sub-ll").one()
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, dt.datetime)
        assert user.last_login_at >= before


def test_last_login_at_updated_on_re_login(anon_client, _db):
    """P1.4: On re-login last_login_at should be updated to recent timestamp."""
    from tests.conftest import _login

    _, Sess = _db
    with Sess() as db:
        db.add(User(email="old@g.com", name="Old", google_sub="sub-re"))
        db.commit()

    before = dt.datetime.now(UTC).replace(tzinfo=None)
    _login(anon_client, {"email": "old@g.com", "sub": "sub-re", "name": "Old"})
    with Sess() as db:
        user = db.query(User).filter_by(google_sub="sub-re").one()
        assert user.last_login_at is not None
        assert user.last_login_at >= before


# ── P1.1 — Delete account (unit) ──────────────────────────────────


def test_delete_user_by_id_removes_user(db_session):
    """delete_user_by_id removes the user row."""
    user = User(email="del@test.com", name="Del", google_sub="sub-del")
    db_session.add(user)
    db_session.flush()
    uid = user.id

    delete_user_by_id(db_session, uid)
    assert db_session.get(User, uid) is None


def test_delete_user_cascades_to_accounts(db_session):
    """delete_user_by_id removes all accounts owned by the user."""
    user = User(email="a@test.com", name="A", google_sub="sub-a")
    db_session.add(user)
    db_session.flush()

    acc = Account(name="Test Acc", user_id=user.id, type="bank", currency="INR")
    db_session.add(acc)
    db_session.flush()

    delete_user_by_id(db_session, user.id)
    assert db_session.query(Account).filter(Account.user_id == user.id).count() == 0


def test_delete_user_cascades_to_transactions(db_session):
    """delete_user_by_id removes all transactions owned by the user."""
    user = User(email="t@test.com", name="T", google_sub="sub-t")
    db_session.add(user)
    db_session.flush()

    acc = Account(name="T Acc", user_id=user.id, type="bank", currency="INR")
    db_session.add(acc)
    db_session.flush()

    tx = Transaction(
        user_id=user.id,
        account_id=acc.id,
        amount=100,
        type=TransactionType.INCOME,
        description="Test",
        date=dt.date(2026, 1, 1),
    )
    db_session.add(tx)
    db_session.flush()

    delete_user_by_id(db_session, user.id)
    assert db_session.query(Transaction).filter(Transaction.user_id == user.id).count() == 0


def test_delete_user_cascades_to_categories_budgets_recurring(db_session):
    """delete_user_by_id removes categories, budgets, and recurring rules."""
    user = User(email="c@test.com", name="C", google_sub="sub-c")
    db_session.add(user)
    db_session.flush()

    cat = Category(name="Food", user_id=user.id, type=CategoryType.EXPENSE)
    db_session.add(cat)
    db_session.flush()

    acc = Account(name="C Acc", user_id=user.id, type="bank", currency="INR")
    db_session.add(acc)
    db_session.flush()

    bgt = Budget(
        category_id=cat.id, user_id=user.id, amount=1000, period=BudgetPeriod.MONTHLY, start_date=dt.date(2026, 1, 1)
    )
    db_session.add(bgt)

    rr = RecurringRule(
        account_id=acc.id,
        user_id=user.id,
        amount=50,
        type=RecurringTransactionType.EXPENSE,
        description="Sub",
        frequency=RecurringFrequency.MONTHLY,
        start_date=dt.date(2026, 1, 1),
    )
    db_session.add(rr)
    db_session.commit()

    delete_user_by_id(db_session, user.id)
    assert db_session.query(Category).filter(Category.user_id == user.id).count() == 0
    assert db_session.query(Budget).filter(Budget.user_id == user.id).count() == 0
    assert db_session.query(RecurringRule).filter(RecurringRule.user_id == user.id).count() == 0


# ── P1.2 — Data export ────────────────────────────────────────────


def test_export_requires_auth(anon_client):
    """GET /api/account/export requires authentication."""
    resp = anon_client.get("/api/account/export")
    assert resp.status_code == 401


def test_export_returns_all_sections(client, db_session):
    """GET /api/account/export returns JSON with all data sections."""
    resp = client.get("/api/account/export")
    assert resp.status_code == 200
    data = resp.json()
    assert "user" in data
    assert "accounts" in data
    assert "transactions" in data
    assert "categories" in data
    assert "budgets" in data
    assert "recurring_rules" in data
    assert data["user"]["email"] == "test@example.com"


def test_export_contains_download_header(client):
    """Export response includes Content-Disposition attachment header."""
    resp = client.get("/api/account/export")
    assert resp.status_code == 200
    assert "attachment;" in resp.headers.get("content-disposition", "")


def test_export_has_exported_at_timestamp(client):
    """Export includes an exported_at ISO timestamp."""
    resp = client.get("/api/account/export")
    data = resp.json()
    assert "exported_at" in data
    assert "T" in data["exported_at"]


def test_get_all_user_data_returns_correct_data(db_session):
    """crud.user.get_all_user_data returns all data for the user."""
    user = User(email="x@test.com", name="X", google_sub="sub-x")
    db_session.add(user)
    db_session.flush()

    acc = Account(name="X Acc", user_id=user.id, type="bank", currency="INR")
    db_session.add(acc)
    db_session.commit()

    data = get_all_user_data(db_session, user.id)
    assert data["user"]["email"] == "x@test.com"
    assert len(data["accounts"]) == 1
    assert data["accounts"][0]["name"] == "X Acc"


# ── P1.1 — Settings and delete pages ──────────────────────────────


def test_settings_page_renders(client):
    """GET /account/settings renders the settings page for authenticated users."""
    resp = client.get("/account/settings")
    assert resp.status_code == 200
    assert "Download my data" in resp.text
    assert "Delete Account" in resp.text


def test_delete_account_page_renders(client):
    """GET /account/delete renders the delete confirmation page."""
    resp = client.get("/account/delete")
    assert resp.status_code == 200
    assert "Permanently delete my account" in resp.text
    assert "Warning" in resp.text


def test_delete_account_page_has_csrf_token(client):
    """P1.1: Delete form includes a fresh, session-bound CSRF token."""
    first = client.get("/account/delete")
    second = client.get("/account/delete")

    assert first.status_code == 200
    assert second.status_code == 200
    assert 'name="csrf_token"' in first.text
    assert 'name="csrf_token"' in second.text
    assert 'name="confirm"' not in first.text
    assert 'name="confirm"' not in second.text

    first_value = first.text.split('name="csrf_token"', 1)[1].split('value="', 1)[1].split('"', 1)[0]
    second_value = second.text.split('name="csrf_token"', 1)[1].split('value="', 1)[1].split('"', 1)[0]

    assert first_value != second_value


def test_settings_page_requires_auth(anon_client):
    """GET /account/settings redirects anonymous to login."""
    resp = anon_client.get("/account/settings", follow_redirects=False)
    assert resp.status_code in (303, 302, 401)


def test_delete_page_requires_auth(anon_client):
    """GET /account/delete redirects anonymous to login."""
    resp = anon_client.get("/account/delete", follow_redirects=False)
    assert resp.status_code in (303, 302, 401)


# ── P1.3 — DSAR via privacy page mailto ───────────────────────────


def test_privacy_page_has_mailto_link(client):
    """P1.3: Privacy page includes a mailto: link for DSAR."""
    resp = client.get("/privacy")
    body = resp.text
    settings = get_settings()
    assert f"mailto:{settings.privacy_email}" in body
