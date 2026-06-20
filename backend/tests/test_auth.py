"""Tests for authentication and multi-user data isolation (§3.8).

Covers:
- Anonymous requests → 401
- Sign-in flow (mocked Google OAuth)
- Session cookie presence / absence / signature
- Logout clears session
- Cross-user isolation: user A's data invisible to user B
- Stale session (deleted user) → 401
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware

import app.models  # noqa: F401 — register all models on Base.metadata
import app.routers.auth as auth_mod
from app.database import Base, get_db
from app.main import app
from app.models.user import User

# ── Helpers ───────────────────────────────────────────────────────


def _mock_oauth(userinfo: dict) -> MagicMock:
    """Build a mock OAuth object that returns *userinfo* on callback."""
    m = MagicMock()
    m.google.authorize_redirect = AsyncMock(
        return_value=RedirectResponse(
            url="https://accounts.google.com/o/oauth2/auth?mock=1", status_code=302
        )
    )
    m.google.authorize_access_token = AsyncMock(
        return_value={"userinfo": userinfo, "access_token": "tok"}
    )
    return m


def _patch_auth_settings():
    """Return a context manager that gives auth module valid OAuth settings."""
    return patch.object(
        auth_mod,
        "settings",
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
        google_redirect_uri="http://localhost/auth/google/callback",
    )


def _login(anon_client: TestClient, userinfo: dict) -> None:
    """Drive the OAuth callback to log in a user.  Verifies via session cookie."""
    oauth = _mock_oauth(userinfo)
    with patch.object(auth_mod, "_ensure_oauth", return_value=oauth):
        anon_client.get("/auth/google/callback")
    assert anon_client.cookies.get("session") is not None


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def _db(tmp_db_path):
    """Yield (engine, session_factory) with all tables created."""
    engine = create_engine(
        f"sqlite:///{tmp_db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    yield engine, factory
    engine.dispose()


@pytest.fixture()
def anon_client(_db):
    """TestClient with real session auth — no get_current_user override.

    HTTPSRedirectMiddleware is removed so the TestClient (which speaks HTTP
    internally) can exercise session-based auth without 307 redirects.
    The auth callback's session_scope is also patched to use the test DB.
    """
    _, Sess = _db

    def _get_db():
        db = Sess()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _session_scope() -> Generator:
        db = Sess()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db

    # Strip HTTPSRedirectMiddleware so HTTP requests reach the handlers.
    # Also set SessionMiddleware to https_only=False so the TestClient
    # (which speaks HTTP) can send/receive the session cookie.
    saved_middleware = list(app.user_middleware)
    saved_stack = app.middleware_stack
    new_user_middleware = []
    for m in app.user_middleware:
        if m.cls is HTTPSRedirectMiddleware:
            continue
        if m.cls is SessionMiddleware:
            m.kwargs["https_only"] = False
        new_user_middleware.append(m)
    app.user_middleware = new_user_middleware
    app.middleware_stack = None

    # Patch session_scope inside auth module to use the test DB.
    scope_patcher = patch.object(auth_mod, "session_scope", _session_scope)
    scope_patcher.start()

    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        scope_patcher.stop()
        app.user_middleware = saved_middleware
        app.middleware_stack = saved_stack
        app.dependency_overrides.pop(get_db, None)


# ── 1. Anonymous access ──────────────────────────────────────────


class TestAnonymousAccess:
    def test_api_accounts_401(self, anon_client):
        assert anon_client.get("/api/accounts").status_code == 401

    def test_api_transactions_401(self, anon_client):
        assert anon_client.get("/api/transactions").status_code == 401

    def test_api_transaction_detail_401(self, anon_client):
        assert anon_client.get("/api/transactions/1").status_code == 401

    def test_api_dashboard_summary_401(self, anon_client):
        assert anon_client.get("/api/dashboard/summary").status_code == 401

    def test_api_dashboard_spending_401(self, anon_client):
        assert anon_client.get("/api/dashboard/spending").status_code == 401

    def test_api_dashboard_category_breakdown_401(self, anon_client):
        assert anon_client.get("/api/dashboard/category-breakdown").status_code == 401

    def test_api_dashboard_budgets_401(self, anon_client):
        assert anon_client.get("/api/dashboard/budgets").status_code == 401

    def test_api_balance_history_401(self, anon_client):
        assert anon_client.get("/api/accounts/1/balance-history").status_code == 401

    def test_api_predictions_expenses_401(self, anon_client):
        assert anon_client.get("/api/predictions/expenses").status_code == 401

    def test_api_predictions_balance_401(self, anon_client):
        assert anon_client.get("/api/predictions/balance").status_code == 401

    def test_accounts_page_401(self, anon_client):
        assert anon_client.get("/accounts").status_code == 401

    def test_dashboard_page_401(self, anon_client):
        assert anon_client.get("/").status_code == 401

    def test_transactions_page_401(self, anon_client):
        assert anon_client.get("/transactions").status_code == 401

    def test_transaction_edit_page_401(self, anon_client):
        assert anon_client.get("/transactions/1/edit").status_code == 401

    def test_categories_page_401(self, anon_client):
        assert anon_client.get("/categories").status_code == 401

    def test_budgets_page_401(self, anon_client):
        assert anon_client.get("/budgets").status_code == 401

    def test_recurring_page_401(self, anon_client):
        assert anon_client.get("/recurring").status_code == 401

    def test_login_page_200(self, anon_client):
        assert anon_client.get("/login").status_code == 200

    def test_healthz_200(self, anon_client):
        assert anon_client.get("/healthz").status_code == 200

    def test_readyz_200(self, anon_client):
        assert anon_client.get("/readyz").status_code == 200


# ── 2. Login flow (mocked Google OAuth) ──────────────────────────


class TestLoginFlow:
    def test_login_redirects_to_google(self, anon_client):
        oauth = _mock_oauth({"email": "u@g.com", "sub": "s", "name": "U"})
        with (
            patch.object(auth_mod, "_ensure_oauth", return_value=oauth),
            _patch_auth_settings(),
        ):
            resp = anon_client.get("/auth/login", follow_redirects=False)
        assert resp.status_code == 302
        assert "accounts.google.com" in resp.headers["location"]

    def test_login_without_credentials_500(self, anon_client):
        with patch.object(auth_mod, "settings") as s:
            s.google_client_id = None
            s.google_client_secret = None
            assert anon_client.get("/auth/login").status_code == 500

    def test_callback_creates_user(self, anon_client, _db):
        _, Sess = _db
        _login(anon_client, {"email": "n@g.com", "sub": "sub-n", "name": "N"})

        with Sess() as db:
            u = db.query(User).filter_by(google_sub="sub-n").one()
            assert u.email == "n@g.com"
            assert u.name == "N"

    def test_callback_upserts_existing(self, anon_client, _db):
        _, Sess = _db
        with Sess() as db:
            db.add(User(email="old@g.com", name="Old", google_sub="sub-e"))
            db.commit()

        _login(anon_client, {"email": "new@g.com", "sub": "sub-e", "name": "Upd"})

        with Sess() as db:
            rows = db.query(User).filter_by(google_sub="sub-e").all()
            assert len(rows) == 1
            assert rows[0].email == "new@g.com"
            assert rows[0].name == "Upd"


# ── 3. Session cookie ────────────────────────────────────────────


class TestSessionCookie:
    def test_no_session_before_login(self, anon_client):
        assert anon_client.get("/api/accounts").status_code == 401
        # SessionMiddleware may set an empty/unsigned cookie but it
        # should not contain a valid session with user_id.
        session_cookie = anon_client.cookies.get("session")
        if session_cookie:
            assert session_cookie == "" or "user_id" not in session_cookie

    def test_session_set_after_login(self, anon_client):
        _login(anon_client, {"email": "u@g.com", "sub": "s", "name": "U"})
        assert anon_client.cookies.get("session") is not None

    def test_tampered_cookie_rejected(self, anon_client):
        _login(anon_client, {"email": "u@g.com", "sub": "s", "name": "U"})
        orig = anon_client.cookies.get("session")
        assert orig is not None
        anon_client.cookies.set("session", orig[:-4] + "XXXX")
        assert anon_client.get("/api/accounts").status_code == 401


# ── 4. Logout ────────────────────────────────────────────────────


class TestLogout:
    def test_logout_clears_session(self, anon_client):
        # Login.
        _login(anon_client, {"email": "u@g.com", "sub": "s", "name": "U"})
        assert anon_client.get("/api/accounts").status_code == 200

        # Logout.
        resp = anon_client.post("/auth/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

        # Session gone.
        assert anon_client.get("/api/accounts").status_code == 401

    def test_logout_redirects_to_login(self, anon_client):
        resp = anon_client.post("/auth/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


# ── 5. Cross-user data isolation ─────────────────────────────────


class TestCrossUserIsolation:
    def test_user_b_cannot_see_user_a_data(self, anon_client, _db):
        _, Sess = _db

        with Sess() as db:
            alice = User(email="alice@g.com", name="Alice", google_sub="sub-a")
            bob = User(email="bob@g.com", name="Bob", google_sub="sub-b")
            db.add_all([alice, bob])
            db.commit()

        # Alice logs in and creates an account.
        _login(anon_client, {"email": "alice@g.com", "sub": "sub-a", "name": "Alice"})

        resp = anon_client.post(
            "/accounts",
            data={
                "name": "A Save",
                "type": "savings",
                "currency": "INR",
                "opening_balance": "100",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 200

        # Switch to Bob.
        anon_client.post("/auth/logout", follow_redirects=False)
        _login(anon_client, {"email": "bob@g.com", "sub": "sub-b", "name": "Bob"})

        # Bob sees nothing.
        assert anon_client.get("/api/accounts").json() == []
        # Bob gets 404 for Alice's account.
        assert anon_client.get("/api/accounts/1").status_code == 404


# ── 6. Stale session ─────────────────────────────────────────────


class TestStaleSession:
    def test_deleted_user_returns_401(self, anon_client, _db):
        _, Sess = _db

        with Sess() as db:
            user = User(email="del@g.com", name="Del", google_sub="sub-del")
            db.add(user)
            db.commit()

        _login(anon_client, {"email": "del@g.com", "sub": "sub-del", "name": "Del"})
        assert anon_client.get("/api/accounts").status_code == 200

        # Delete the user from DB.
        with Sess() as db:
            db.query(User).filter_by(google_sub="sub-del").delete()
            db.commit()

        # Session still exists but user is gone → 401.
        assert anon_client.get("/api/accounts").status_code == 401
