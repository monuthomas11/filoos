# Filoos — Reporting Module Implementation Plan

> **Purpose**: Full reporting module with Income/Expense, Balance Trend, and Cash Flow reports.
> **Status**: Planning → Ready for Implementation
> **Scope**: New module only — no breaking changes to existing functionality.

---

## 1. Executive Summary

This plan adds a dedicated **Reporting module** to Filoos, complementing the existing dashboard charts with full, exportable reports. The module provides:

- **Income/Expense reports** — period comparison, category drill-down, waterfall view
- **Balance Trend reports** — multi-account balance history, combined net worth
- **Cash Flow reports** — inflows vs outflows, net cash position, burn rate

**Key constraint**: All existing functionality (dashboard, transactions, budgets, predictions, recurring rules) must continue working unchanged after implementation.

---

## 2. Architecture Overview

| Layer | File/Location | Purpose |
|-------|---------------|---------|
| **Service** | `app/services/reporting.py` | Core report generation logic (reuses `analytics.py` + new functions) |
| **Router (API)** | `app/routers/reports.py` | JSON endpoints for charts/data + export endpoints |
| **Router (HTML)** | `app/routers/pages.py` (add route) | `/reports` page |
| **Template** | `app/templates/reports/` | `list.html` (main), `partials/` for widgets |
| **Static JS** | `app/static/js/reports.js` | Chart rendering, filter handling, export triggers |
| **Tests** | `backend/tests/test_reports.py` | Unit + integration tests |

**Dependency Chain** (no circular imports):
```
pages.py → templates, reporting.py
reporting.py → analytics.py, crud/account, crud/transaction, models/*
reports.py → reporting.py, deps
```

---

## 3. Report Types & Data Requirements

### 3.1 Income/Expense Report

| Component | Description | Data Source |
|-----------|-------------|-------------|
| **KPI Cards** | Total income, total expense, net, savings rate for period | `analytics.monthly_summary()` |
| **Period Comparison Bar** | Side-by-side bars (this period vs previous) | `analytics.monthly_summary()` x2 |
| **Category Breakdown** | Stacked bar or doughnut of expenses by category | `analytics.category_breakdown()` |
| **Monthly Trend** | Line chart of income/expense over time | `analytics.monthly_summary()` iterated |
| **Waterfall** | Income → Expense → Net flow | Computed from monthly summary |

**API Response Shape**:
```json
{
  "period": {"start": "2026-01-01", "end": "2026-01-31"},
  "summary": {"income": "50000.00", "expense": "32000.00", "net": "18000.00", "savings_rate": 36.0},
  "category_breakdown": [{"label": "Rent", "amount": "15000.00", "color": "#4f46e5"}],
  "monthly_trend": [{"month": "2026-01", "income": "50000.00", "expense": "32000.00"}],
  "comparison": { /* previous period or year-ago data */ }
}
```

### 3.2 Balance Trend Report

| Component | Description | Data Source |
|-----------|-------------|-------------|
| **Multi-Account Lines** | Separate line per account | `analytics.balance_history()` per account |
| **Combined Net Worth** | Sum of all account balances over time | Computed aggregate |
| **Account Toggle** | Show/hide individual accounts | Client-side filter |
| **Growth Rate** | % change over period | Computed from start/end |

**API Response Shape**:
```json
{
  "period": {"start": "2026-01-01", "end": "2026-03-31"},
  "accounts": [
    {
      "account_id": 1, "name": "HDFC Bank", "color": "#4f46e5",
      "series": [{"date": "2026-01-01", "balance": "125000.00"}]
    }
  ],
  "net_worth": [{"date": "2026-01-01", "balance": "450000.00"}],
  "growth": {"start": "400000.00", "end": "450000.00", "change_pct": 12.5}
}
```

### 3.3 Cash Flow Report

| Component | Description | Data Source |
|-----------|-------------|-------------|
| **Inflows vs Outflows** | Bar chart of income (in) vs expense (out) | `analytics.monthly_summary()` |
| **Net Cash Flow** | Line of net (income - expense) per period | Computed |
| **Cumulative Cash Flow** | Running total of net flows | Computed |
| **Burn Rate** | Average daily expense over period | `analytics.daily_spending()` |
| **Runway** | Days until zero balance at burn rate | From forecasting service |

**API Response Shape**:
```json
{
  "period": {"start": "2026-01-01", "end": "2026-03-31"},
  "flows": [
    {"period": "2026-01", "inflow": "50000.00", "outflow": "32000.00", "net": "18000.00"}
  ],
  "cumulative": [{"period": "2026-01", "balance": "18000.00"}],
  "metrics": {"burn_rate": "1066.67", "runway_days": 42}
}
```

---

## 4. Filter Options (Unified Across All Reports)

| Filter | Type | Options | Default | API Param |
|--------|------|---------|---------|-----------|
| **Period** | Select | Current month, Previous month, Last 3 months, Last 6 months, This year, Last year, Custom range, All time | Current month | `period` |
| **Date Range** | Date pickers | Any valid range (start/end) | — | `start_date`, `end_date` |
| **Accounts** | Multi-select | All accounts + individual | All | `account_ids` (comma-sep) |
| **Categories** | Multi-select | All categories + individual (filtered by type) | All | `category_ids` (comma-sep) |
| **Transaction Types** | Checkboxes | Income, Expense, Transfer | Income + Expense | `types` (comma-sep) |
| **Grouping** | Select | Auto, Day, Week, Month, Quarter, Year | Auto | `group_by` |
| **Comparison** | Toggle | None, Previous period, Same period last year | None | `compare` |

**Filter Validation Rules**:
- `start_date` must be ≤ `end_date`
- `account_ids` must reference existing accounts
- `category_ids` must reference existing categories
- `group_by=auto` picks based on date range duration:
  - ≤31 days → day
  - ≤90 days → week
  - ≤365 days → month
  - >365 days → quarter

**Filter Persistence**:
- Filters stored in `localStorage` key `ff-report-filters`
- Auto-populated on page load
- Reset button clears localStorage and resets to defaults

---

## 5. API Endpoints

| Method | Path | Description | Query Params |
|--------|------|-------------|--------------|
| GET | `/api/reports/income-expense` | Income/Expense summary + breakdown | All filters |
| GET | `/api/reports/balance-trend` | Multi-account balance history | All filters |
| GET | `/api/reports/cash-flow` | Cash flow statement data | All filters |
| GET | `/api/reports/export` | Export current report as CSV | `format=csv`, report type, all filters |
| GET | `/reports` | HTML page (main reports view) | — |

**Response Format**: All API endpoints return JSON with consistent envelope:
```json
{
  "ok": true,
  "data": { /* report-specific payload */ },
  "meta": { "generated_at": "2026-06-10T12:00:00", "filters": {...} }
}
```

**Error Response**:
```json
{
  "ok": false,
  "error": { "code": "INVALID_DATE_RANGE", "message": "start_date must be before end_date" }
}
```

---

## 6. Service Layer Design (`services/reporting.py`)

### 6.1 Reused Functions (No Changes)

These existing functions are reused directly — **no modifications to `analytics.py`**:

| Function | Used By |
|----------|---------|
| `monthly_summary()` | Income/Expense, Cash Flow |
| `daily_spending()` | Cash Flow burn rate |
| `category_breakdown()` | Income/Expense category drill-down |
| `budget_progress()` | Referenced but not primary |
| `balance_history()` | Balance Trend |
| `_resolve_date_range()` | All reports (date parsing) |

### 6.2 New Functions

```python
def income_expense_report(
    db: Session,
    start_date: datetime.date,
    end_date: datetime.date,
    account_ids: list[int] | None = None,
    category_ids: list[int] | None = None,
    compare: str | None = None,  # "previous_period" | "previous_year"
) -> dict:
    """Income/Expense report with optional comparison."""
    # 1. Get period summary (reuses monthly_summary)
    # 2. Get category breakdown (reuses category_breakdown)
    # 3. Get monthly trend (iterates months in range)
    # 4. If compare, compute comparison period and delta
    # Return structured dict

def balance_trend_report(
    db: Session,
    start_date: datetime.date,
    end_date: datetime.date,
    account_ids: list[int] | None = None,
    group_by: str = "day",
) -> dict:
    """Multi-account balance trend with net worth."""
    # 1. List accounts (filtered)
    # 2. For each account, call balance_history()
    # 3. Compute combined net_worth series
    # 4. Compute growth metrics
    # Return structured dict

def cash_flow_report(
    db: Session,
    start_date: datetime.date,
    end_date: datetime.date,
    account_ids: list[int] | None = None,
    group_by: str = "month",
) -> dict:
    """Cash flow statement with burn rate."""
    # 1. Get monthly income/expense (reuses monthly_summary)
    # 2. Compute net cash flow per period
    # 3. Compute cumulative cash flow
    # 4. Compute burn rate (daily_spending average)
    # 5. Compute runway (from forecasting or manual)
    # Return structured dict

def compute_burn_rate(
    db: Session,
    start_date: datetime.date,
    end_date: datetime.date,
    account_ids: list[int] | None = None,
) -> dict:
    """Average daily expense and runway."""
    # Uses daily_spending() for the period
    # Returns {"burn_rate": str, "runway_days": int | None}

def export_to_csv(report_data: dict, report_type: str) -> bytes:
    """Convert report dict to CSV bytes."""
    # Uses Python csv module
    # Returns UTF-8 BOM-encoded CSV for Excel compatibility
```

### 6.3 Filter Normalization

Shared helper to parse and validate filter params:

```python
def normalize_filters(
    period: str | None,
    start_date: str | None,
    end_date: str | None,
    account_ids: str | None,  # comma-separated
    category_ids: str | None,
    types: str | None,
    group_by: str | None,
    compare: str | None,
) -> ReportFilters:
    """Parse and validate all filter params into a typed dict."""
    # 1. Resolve date range (reuse _resolve_date_range or custom)
    # 2. Parse comma-separated IDs into lists
    # 3. Validate group_by, compare
    # 4. Return ReportFilters dataclass
```

---

## 7. UI/UX Design

### 7.1 Page Structure (`/reports`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Reports                                            [Export ▼] │
├─────────────────────────────────────────────────────────────────┤
│ [Period ▼] [Date Range] [Accounts ▼] [Categories ▼] [Types ▼] │
│ [Group By ▼] [Compare ▼]                        [Reset Filters]│
├─────────────────────────────────────────────────────────────────┤
│ [Income/Expense]  [Balance Trend]  [Cash Flow]    ← Tabs       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  KPI Cards (if Income/Expense tab selected):                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Income   │ │ Expense  │ │ Net      │ │ Savings  │          │
│  │ ₹50,000  │ │ ₹32,000  │ │ ₹18,000  │ │ 36%      │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                 │
│  Charts (per tab):                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │  Bar Chart          │  │  Category Doughnut   │              │
│  │  (Period Compare)   │  │  (Expense Breakdown) │              │
│  └─────────────────────┘  └─────────────────────┘              │
│  ┌─────────────────────────────────────────────┐              │
│  │  Monthly Trend Line Chart                   │              │
│  │  (Income vs Expense over time)              │              │
│  └─────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Tab Content

**Income/Expense Tab**:
- KPI row: Income, Expense, Net, Savings Rate
- Period comparison bar chart
- Category breakdown (stacked bar or doughnut)
- Monthly trend line chart (dual line: income + expense)

**Balance Trend Tab**:
- KPI row: Starting balance, Ending balance, Growth %
- Multi-line chart (one line per account)
- Combined net worth line
- Account toggle checkboxes

**Cash Flow Tab**:
- KPI row: Total Inflow, Total Outflow, Net Cash, Burn Rate
- Inflow/Outflow grouped bar chart
- Net cash flow line chart
- Cumulative cash flow area chart
- Runway indicator

### 7.3 Export Menu

```
[Export ▼]
├── CSV (Income/Expense)
├── CSV (Balance Trend)
├── CSV (Cash Flow)
└── PDF (All reports)  ← Phase 2, optional
```

CSV export triggers immediate download. PDF requires server-side rendering (weasyprint/reportlab — deferred to v2).

---

## 8. Implementation Phases

| Phase | Deliverables | Files | Est. Effort | Dependencies |
|-------|--------------|-------|-------------|--------------|
| **Phase 1: Core Service** | `reporting.py` with 3 report functions + filter normalization | `app/services/reporting.py`, `backend/tests/test_reports.py` | 2 days | None |
| **Phase 2: API Layer** | `/api/reports/*` endpoints, filter validation, CSV export | `app/routers/reports.py`, update `app/main.py` | 1 day | Phase 1 |
| **Phase 3: UI Page** | `/reports` HTML page, filter bar, tabbed layout, Chart.js integration | `app/templates/reports/list.html`, `app/templates/reports/partials/`, `app/static/js/reports.js`, update `app/routers/pages.py` | 3 days | Phase 2 |
| **Phase 4: Filter Persistence** | localStorage integration, filter state management | `app/static/js/reports.js` (extend), `app/templates/reports/list.html` | 0.5 days | Phase 3 |
| **Phase 5: Polish** | Loading states, empty states, error handling, a11y, responsive | All Phase 3 files | 1 day | Phase 4 |

**Total: ~7.5 days**

---

## 9. Existing Functionality Validation Checklist

**CRITICAL**: The following must remain unchanged after implementation:

| Area | What to Test | How to Validate |
|------|--------------|-----------------|
| **Dashboard** | All charts render, KPIs load, period filter works | Manual: load `/`, verify charts, switch periods |
| **Dashboard API** | `/api/dashboard/*` endpoints return correct JSON | `pytest backend/tests/test_dashboard.py` |
| **Transactions** | CRUD operations, filters, transfers | `pytest backend/tests/test_transactions.py` |
| **Accounts** | CRUD operations, balance computation | `pytest backend/tests/test_accounts.py` |
| **Categories** | CRUD operations, assignment to transactions | `pytest backend/tests/test_categories.py` |
| **Budgets** | CRUD operations, progress calculation | `pytest backend/tests/test_budgets.py` |
| **Recurring Rules** | Materialization, preview, CRUD | `pytest backend/tests/test_recurring.py` |
| **Predictions** | Expense forecast, balance projection, runway | `pytest backend/tests/test_predictions.py` |
| **Smoke Tests** | Health check, dashboard render, static CSS | `pytest backend/tests/test_smoke.py` |
| **Routes** | All existing routes still registered | `app.main.py` — no routes removed |
| **Templates** | No existing template modified | Only new templates added |
| **Models** | No schema changes | Only new service/router files |
| **Migrations** | No new migrations required | Reports use existing data |

**Validation Commands** (run after each phase):
```bash
# Full test suite
cd backend && pytest -v

# Lint check
cd backend && ruff check .

# Manual smoke test
.\scripts\dev.ps1
# Visit http://127.0.0.1:8000 — verify dashboard loads
# Visit http://127.0.0.1:8000/transactions — verify list loads
# Visit http://127.0.0.1:8000/reports — verify new page loads
```

**Risk Mitigation**:
1. **No existing files modified** except:
   - `app/main.py` — add one router import + include_router (1 line each)
   - `app/routers/pages.py` — add one route (5 lines)
2. **No existing functions modified** — only new functions added
3. **No existing templates modified** — only new templates created
4. **No existing tests modified** — only new tests added
5. **No database migrations** — all data already exists

---

## 10. Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate `reporting.py` service** | Keeps analytics (dashboard-focused) separate from reporting (flexible, exportable) |
| **Unified filter params** | Single filter model reused across all 3 reports + export |
| **Chart.js for all charts** | Already in stack, consistent look, no new dependencies |
| **CSV first, PDF later** | CSV is trivial with Python stdlib; PDF needs new dep (weasyprint) — deferred |
| **HTMX for filter updates** | Consistent with app pattern; partial chart re-render via JS |
| **Server-side aggregation** | SQLite can handle the data volumes; keeps client light |
| **No schema changes** | Reports are read-only views of existing data |

---

## 11. Dependencies

| Dependency | Version | Purpose | Required? |
|------------|---------|---------|-----------|
| `pandas` | Already installed | Data manipulation (optional, can use stdlib) | No |
| `weasyprint` | — | PDF generation | No (Phase 2) |
| `reportlab` | — | PDF generation (alternative) | No (Phase 2) |

**New dependencies for Phase 1-3: None.** All functionality uses existing stack (FastAPI, SQLAlchemy, Chart.js).

---

## 12. Files to Create/Modify

| File | Action | Lines (est.) | Notes |
|------|--------|--------------|-------|
| `app/services/reporting.py` | **Create** | ~250 | Core report logic |
| `app/routers/reports.py` | **Create** | ~120 | API endpoints |
| `app/routers/pages.py` | **Modify** | +5 | Add `GET /reports` route |
| `app/main.py` | **Modify** | +2 | Import + mount reports_router |
| `app/templates/reports/list.html` | **Create** | ~300 | Main page with tabs |
| `app/templates/reports/partials/income_expense.html` | **Create** | ~100 | Income/Expense tab content |
| `app/templates/reports/partials/balance_trend.html` | **Create** | ~80 | Balance Trend tab content |
| `app/templates/reports/partials/cash_flow.html` | **Create** | ~80 | Cash Flow tab content |
| `app/templates/reports/partials/filter_bar.html` | **Create** | ~120 | Shared filter bar |
| `app/static/js/reports.js` | **Create** | ~400 | Charts, filters, export |
| `backend/tests/test_reports.py` | **Create** | ~200 | Unit + integration tests |
| **TOTAL** | | ~1,655 | |

---

## 13. Questions for Clarification

1. **Export formats priority**: CSV only for v1, or PDF required immediately?
2. **Comparison periods**: Is "vs same period last year" needed, or just "vs previous period"?
3. **Cash flow categorization**: Should transfers be excluded (standard accounting) or shown as financing activity?
4. **Multi-currency**: Not in scope (single currency), but confirm?
5. **Scheduled reports**: Out of scope for v1, but worth designing hooks for?

---

## 14. Success Criteria

| Criterion | Metric | Validation |
|-----------|--------|------------|
| **No regressions** | 202 tests pass | `pytest` |
| **New tests pass** | 20+ new tests | `pytest test_reports.py` |
| **Linter clean** | 0 warnings | `ruff check .` |
| **Reports load** | 200 OK | Manual test `/reports` |
| **Charts render** | No JS errors | Browser console |
| **Filters work** | Data updates on filter change | Manual test |
| **Export works** | CSV downloads correctly | Manual test |
| **Existing pages unchanged** | Dashboard, Transactions, etc. load normally | Manual test |

---

*Plan created: 2026-06-10*
*Estimated start: Phase 1-2 (service + API) → 3 days*
*Estimated completion: All phases → 7.5 days*
