"""pytest fixtures shared across the test suite."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Allow testserver for TestClient before app settings are loaded.
os.environ.setdefault("FF_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

# Import all models so their tables are registered on Base.metadata.
import app.models  # noqa: E402, F401
from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.deps import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402

# ------------------------------------------------------------------
# Temporary SQLite file for each test so the TestClient background
# thread and the test share the same on-disk database.
# ------------------------------------------------------------------


@pytest.fixture(scope="function")
def tmp_db_path() -> Generator[Path, None, None]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = Path(tmp.name)
    tmp.close()  # just need the name; SQLAlchemy will create it.
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


@pytest.fixture(scope="function")
def db_session(tmp_db_path: Path) -> Generator[Session, None, None]:
    """Fresh on-disk SQLite session for each test."""
    url = f"sqlite:///{tmp_db_path.as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
def client(tmp_db_path: Path) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired to the same on-disk DB as db_session."""
    url = f"sqlite:///{tmp_db_path.as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Create a default test user and override authentication dependency.
    with TestingSessionLocal() as db:
        user = User(email="test@example.com", name="Test User", google_sub="test-sub")
        db.add(user)
        db.commit()
        db.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture(scope="session")
def settings():
    return get_settings()


# ------------------------------------------------------------------
# Anonymous-client fixtures for end-to-end auth tests (OAuth callback etc.)
# ------------------------------------------------------------------

import app.routers.auth as auth_mod  # noqa: E402


def _mock_oauth(userinfo: dict) -> MagicMock:
    """Build a mock OAuth object that returns *userinfo* on callback."""
    m = MagicMock()
    m.google.authorize_redirect = AsyncMock(
        return_value=RedirectResponse(
            url="https://accounts.google.com/o/oauth2/auth?mock=1", status_code=302
        )
    )
    m.google.authorize_access_token = AsyncMock(return_value={"userinfo": userinfo, "access_token": "tok"})
    return m


def _login(anon_client: TestClient, userinfo: dict) -> None:
    """Drive the OAuth callback to log in a user.  Verifies via session cookie."""
    oauth = _mock_oauth(userinfo)
    with patch.object(auth_mod, "_ensure_oauth", return_value=oauth):
        anon_client.get("/auth/google/callback")
    assert anon_client.cookies.get("session") is not None


@pytest.fixture()
def _db(tmp_db_path: Path):
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
