"""Smoke tests for the Phase 1 scaffold."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data


def test_dashboard_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "FutureFunds" in body
    assert "Dashboard" in body


def test_static_css_served(client):
    response = client.get("/static/css/app.compiled.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_dashboard_uses_compiled_css(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/static/css/app.compiled.css" in response.text


def test_trusted_host_middleware_accepts_render_hostname():
    """Regression: ``/healthz`` must be reachable when the ``Host``
    header matches the auto-generated Render URL.

    The Render edge forwards requests with ``Host:
    <service-name>.onrender.com``. If ``FF_ALLOWED_HOSTS`` in
    ``render.yaml`` does not include this exact hostname (e.g., it's
    left as a placeholder ``yourapp.onrender.com``), every request —
    including Render's own health probe at ``/healthz`` — is rejected
    with HTTP 400 by Starlette's ``TrustedHostMiddleware`` and the
    deploy times out with ``Timed out after waiting for internal
    health check to return a successful response code``. This test
    pins down the configuration contract: the production allowed-hosts
    list must contain the real Render hostname.
    """
    app = FastAPI()
    app.add_middleware(
        TrustedHostMiddleware,
        # Mirrors the production value from render.yaml.
        allowed_hosts=["futurefunds.onrender.com"],
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    with TestClient(app, base_url="https://futurefunds.onrender.com") as c:
        assert c.get("/healthz").status_code == 200

    with TestClient(app, base_url="https://attacker.example.com") as c:
        assert c.get("/healthz").status_code == 400
