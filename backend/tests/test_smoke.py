"""Smoke tests for the Phase 1 scaffold."""


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
    response = client.get("/static/css/app.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
