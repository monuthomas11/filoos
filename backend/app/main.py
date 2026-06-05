"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import ensure_data_dir, session_scope

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan: ensure SQLite dir exists; auto-materialize recurring rules."""
    ensure_data_dir()
    if settings.recurring_auto_materialize:
        from app.services.recurring import materialize_all

        with session_scope() as db:
            materialize_all(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)


# Static files (CSS, JS, images).
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.routers.accounts import router as accounts_router  # noqa: E402
from app.routers.budgets import router as budgets_router  # noqa: E402
from app.routers.categories import router as categories_router  # noqa: E402
from app.routers.dashboard import router as dashboard_router  # noqa: E402
from app.routers.pages import router as pages_router  # noqa: E402
from app.routers.recurring import router as recurring_router  # noqa: E402
from app.routers.transactions import router as transactions_router  # noqa: E402

app.include_router(pages_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(categories_router)
app.include_router(budgets_router)
app.include_router(recurring_router)
app.include_router(dashboard_router)


# ---------------------------------------------------------------------------
# Health check (kept on root for quick probing)
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "app": settings.app_name}
