"""pytest fixtures shared across the test suite."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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
