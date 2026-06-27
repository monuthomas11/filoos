"""FastAPI application entry point."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings, get_settings
from app.database import ensure_data_dir, session_scope
from app.deps import _NotAuthenticated
from app.logging_config import configure_logging
from app.templates import templates

# Logging must be configured before any module under ``app.*`` acquires a
# logger, otherwise their handlers are set up against the root defaults.
configure_logging()
logger = logging.getLogger("app")

BASE_DIR = Path(__file__).resolve().parent
startup_settings = get_settings()
logger.info(
    "starting Filoos",
    extra={
        "version": "0.1.0",
        "env": startup_settings.app_env,
        "debug": startup_settings.debug,
    },
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan: ensure SQLite dir exists."""
    ensure_data_dir()
    yield
    logger.info("Filoos shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application with environment-dependent settings."""
    settings = settings or get_settings()
    if settings.app_env != "development" and not settings.privacy_email:
        raise RuntimeError("FF_PRIVACY_EMAIL must be set in production")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )

    # Session + security middleware (Phase 2)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret or "",
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.session_cookie_secure,
    )
    # HTTPS redirects are applied when each app instance is constructed so tests
    # can patch the middleware stack after import without changing the app factory.
    if not settings.is_development:
        app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[h.strip() for h in settings.allowed_hosts.split(",") if h.strip()],
    )

    # ---------------------------------------------------------------------------
    # Auth exception handler — redirect browsers to /login on 401
    # ---------------------------------------------------------------------------

    @app.exception_handler(_NotAuthenticated)
    async def not_authenticated_handler(request: Request, exc: _NotAuthenticated):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/login", status_code=303)
        return Response(status_code=401, content=exc.detail)

    # ---------------------------------------------------------------------------
    # Request logging middleware
    # ---------------------------------------------------------------------------

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log one line per request with method, path, status, duration, request_id."""
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )
        response.headers["x-request-id"] = request_id
        return response

    # ---------------------------------------------------------------------------
    # Error handlers
    # ---------------------------------------------------------------------------

    @app.exception_handler(404)
    async def not_found_handler(_request: Request, _exc: HTTPException) -> HTMLResponse:
        return templates.TemplateResponse(_request, "404.html", status_code=404)

    @app.exception_handler(Exception)
    async def server_error_handler(request: Request, exc: Exception) -> HTMLResponse:
        if isinstance(exc, HTTPException):
            raise exc
        logger.exception(
            "unhandled exception",
            extra={"path": request.url.path, "method": request.method},
        )
        return templates.TemplateResponse(request, "500.html", status_code=500)

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
    from app.routers.auth import router as auth_router  # noqa: E402
    from app.routers.budgets import router as budgets_router  # noqa: E402
    from app.routers.categories import router as categories_router  # noqa: E402
    from app.routers.dashboard import router as dashboard_router  # noqa: E402
    from app.routers.export import router as export_router  # noqa: E402
    from app.routers.pages import router as pages_router  # noqa: E402
    from app.routers.predictions import router as predictions_router  # noqa: E402
    from app.routers.recurring import router as recurring_router  # noqa: E402
    from app.routers.transactions import router as transactions_router  # noqa: E402

    app.include_router(pages_router)
    app.include_router(accounts_router)
    app.include_router(transactions_router)
    app.include_router(categories_router)
    app.include_router(budgets_router)
    app.include_router(recurring_router)
    app.include_router(dashboard_router)
    app.include_router(predictions_router)
    app.include_router(export_router)
    app.include_router(auth_router)

    # ---------------------------------------------------------------------------
    # Health check (kept on root for quick probing)
    # ---------------------------------------------------------------------------

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Liveness probe. Returns 200 as long as the process is alive."""
        return {"status": "ok", "app": settings.app_name}

    @app.get("/readyz")
    async def readyz(response: Response) -> dict[str, str]:
        """Readiness probe.

        Verifies that the database is reachable and that core settings are sane.
        Returns 503 if any check fails so a load balancer / orchestrator can
        stop sending traffic.
        """
        checks: dict[str, str] = {}
        healthy = True

        try:
            with session_scope() as db:
                db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except SQLAlchemyError as exc:
            healthy = False
            checks["database"] = f"error: {exc.__class__.__name__}"
            logger.error("readiness check: database unreachable", exc_info=exc)

        try:
            checks["settings"] = "ok" if settings.app_name else "missing"
            if not settings.app_name:
                healthy = False
        except Exception as exc:  # pragma: no cover — defensive
            healthy = False
            checks["settings"] = f"error: {exc.__class__.__name__}"

        response.status_code = 200 if healthy else 503
        return {"status": "ok" if healthy else "degraded", **checks}

    return app


app = create_app()
