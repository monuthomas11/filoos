"""Authentication routes: Google OAuth login, callback, logout, and account deletion."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud.user import delete_user_by_id
from app.database import get_db, session_scope
from app.deps import get_current_user
from app.models.user import User
from app.templates import templates

router = APIRouter()
settings = get_settings()
DELETE_ACCOUNT_CSRF_SESSION_KEY = "delete_account_csrf_token"


def _ensure_oauth() -> OAuth:
    oauth = OAuth()
    oauth.register(
        "google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


@router.get("/auth/login")
async def login(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(500, "Google OAuth not configured")
    oauth = _ensure_oauth()
    redirect_uri = settings.google_redirect_uri or str(
        request.url.replace(path="/auth/google/callback")
    )
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def callback(request: Request):
    oauth = _ensure_oauth()
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:  # pragma: no cover - auth flow
        raise HTTPException(400, f"OAuth error: {exc}") from exc

    userinfo = token.get("userinfo") or {}
    if not userinfo and token.get("id_token"):
        try:
            userinfo = await oauth.google.parse_id_token(request, token)
        except Exception:
            userinfo = {}

    if not userinfo:
        resp = await oauth.google.get("userinfo", token=token)
        userinfo = resp.json()

    email = userinfo.get("email")
    sub = userinfo.get("sub")
    name = userinfo.get("name") or email or ""
    if not email or not sub:
        raise HTTPException(400, "Failed to obtain user info from Google")

    with session_scope() as db:
        user = db.query(User).filter_by(google_sub=sub).one_or_none()
        if user is None:
            user = User(email=email, name=name, google_sub=sub)
            user.last_login_at = datetime.now(UTC)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.email = email
            user.name = name
            user.last_login_at = datetime.now(UTC)
            db.add(user)
            db.commit()
            db.refresh(user)

        request.session["user_id"] = user.id

    return RedirectResponse(url="/")


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Sign In"})


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


def _issue_delete_account_csrf_token(request: Request) -> str:
    """Create a one-time CSRF token bound to the current session."""
    token = secrets.token_urlsafe(32)
    request.session[DELETE_ACCOUNT_CSRF_SESSION_KEY] = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
    return token


def _validate_delete_account_csrf_token(request: Request, submitted_token: str | None) -> None:
    """Validate the delete-account CSRF token from the submitted form."""
    expected_token = request.session.get(DELETE_ACCOUNT_CSRF_SESSION_KEY)
    if not expected_token or not submitted_token:
        raise HTTPException(400, "Invalid confirmation")

    submitted_digest = hashlib.sha256(submitted_token.encode("utf-8")).hexdigest()
    if submitted_digest != expected_token:
        raise HTTPException(400, "Invalid confirmation")

    request.session.pop(DELETE_ACCOUNT_CSRF_SESSION_KEY, None)


@router.post("/auth/delete-account")
async def delete_account(
    request: Request,
    csrf_token: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Permanently delete the authenticated user and all associated data.

    Requires a per-session CSRF token to mitigate CSRF.
    """
    _validate_delete_account_csrf_token(request, csrf_token)
    request.session.clear()
    delete_user_by_id(db, user.id)
    return RedirectResponse(url="/login", status_code=303)
