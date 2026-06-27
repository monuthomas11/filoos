"""Tests for privacy-related routes and content."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.main import create_app


def test_privacy_page_returns_200_anonymous(client):
    """GET /privacy returns 200 for an anonymous (logged-out) request."""
    response = client.get("/privacy")
    assert response.status_code == 200


def test_privacy_page_contains_key_sections(client):
    """Privacy page includes the core transparency sections."""
    response = client.get("/privacy")
    body = response.text
    assert "What personal data we collect" in body
    assert "Your rights" in body
    assert "Contact" in body


def test_privacy_page_contains_lawful_basis(client):
    """P0.4: Policy states the lawful basis for processing."""
    response = client.get("/privacy")
    body = response.text
    assert "Why we use your data" in body
    assert "Contract" in body
    assert "Legitimate interest" in body


def test_privacy_page_discloses_processors(client):
    """P0.5: Policy lists every third-party processor actually used."""
    response = client.get("/privacy")
    body = response.text
    assert "Google LLC" in body
    assert "Render" in body
    assert "Neon" in body
    assert "unpkg.com" in body
    assert "jsdelivr.com" in body


def test_privacy_page_has_privacy_email(client):
    """P0.3: Policy surfaces the privacy contact email from settings."""
    settings = get_settings()
    response = client.get("/privacy")
    body = response.text
    assert settings.privacy_email in body
    assert "{{ privacy_email }}" not in body


def test_terms_page_returns_200_anonymous(client):
    """GET /terms returns 200 for an anonymous request."""
    response = client.get("/terms")
    assert response.status_code == 200


def test_login_page_links_point_to_real_routes(client):
    """P0.2: login.html Privacy and Terms links resolve to real routes."""
    response = client.get("/login")
    body = response.text
    assert 'href="/privacy"' in body
    assert 'href="/terms"' in body


def test_dashboard_footer_has_privacy_links(client):
    """P0.1: Footer on authenticated pages links to /privacy and /terms."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'href="/privacy"' in body
    assert 'href="/terms"' in body


def test_cookie_notice_mentions_strictly_necessary_cookie(client):
    """P2.1: A cookie notice is shown to explain the session cookie."""
    response = client.get("/")
    body = response.text
    assert "strictly-necessary session cookie" in body.lower()
    assert "/privacy" in body


def test_docs_endpoints_are_disabled_in_production():
    """P2.3: Interactive docs are disabled when the app runs in production."""
    app = create_app(Settings(app_env="production", debug=False, session_secret="test-secret"))
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
