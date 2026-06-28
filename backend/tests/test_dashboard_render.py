"""Test that the dashboard HTML page renders correctly."""
from fastapi.testclient import TestClient


def test_dashboard_page_renders(client: TestClient):
    """Verify the dashboard HTML page renders with all key elements."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Core structure
    assert "Dashboard" in html
    assert "Your balance" in html
    assert "Accounts" in html
    assert "Add transaction" in html

    # Interactive elements
    assert "period-select" in html
    assert "horizon-select" in html

    # Chart canvases
    assert "balance-trend-chart" in html
    assert "spending-chart" in html
    assert "category-chart" in html

    # Sections
    assert "budget-progress-container" in html

    # Design system tokens
    assert "rounded-xl" in html
    assert "dark:" in html
    assert "bg-accent-600" in html

    # Hero + KPI elements
    assert "hero-net-text" in html
    assert "hero-net-period" in html
    assert "kpi-income" in html
    assert "kpi-expense" in html
    assert "kpi-savings-rate" in html

    # Account section (empty state since test has no accounts)
    assert "Your accounts will live here" in html

    # Dark mode support
    assert "dark:border-neutral-800" in html
    assert "dark:bg-neutral-900" in html

    # No banned patterns
    assert "gradient-text" not in html

    print(f"Page rendered: {len(html)} bytes, status={resp.status_code}")
