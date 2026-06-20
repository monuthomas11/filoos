"""Authentication routes: Google OAuth login, callback, logout."""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.database import session_scope
from app.models.user import User
from app.templates import templates

router = APIRouter()
settings = get_settings()


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
    # Prefer id_token parsing when available
    if not userinfo and token.get("id_token"):
        try:
            userinfo = await oauth.google.parse_id_token(request, token)
        except Exception:
            userinfo = {}

    # Fallback: request the userinfo endpoint
    if not userinfo:
        resp = await oauth.google.get("userinfo", token=token)
        userinfo = resp.json()

    email = userinfo.get("email")
    sub = userinfo.get("sub")
    name = userinfo.get("name") or email or ""
    if not email or not sub:
        raise HTTPException(400, "Failed to obtain user info from Google")

    # Upsert user
    with session_scope() as db:
        user = db.query(User).filter_by(google_sub=sub).one_or_none()
        if user is None:
            user = User(email=email, name=name, google_sub=sub)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.email = email
            user.name = name
            user.last_login_at = None
            db.add(user)
            db.commit()

        # Write user_id into session cookie
        request.session["user_id"] = user.id

    return RedirectResponse(url="/")


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Sign In"})
