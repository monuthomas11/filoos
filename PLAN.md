# FutureFunds - Living Plan & Design Document

> This document is the source of truth for FutureFunds architecture, design, and roadmap. It is updated as each phase is implemented.
>
> **For a quick "where are we right now?" snapshot** (current phase, what was built, what to do next), see [`STATUS.md`](./STATUS.md). **For setup and usage**, see [`README.md`](./README.md).

## 1. Project Overview

**FutureFunds** is a personal expense tracker built around a lightweight, minimal UI and a small but capable forecasting engine. The product focuses on:

- **Multi-account tracking** (cash, bank, credit card, savings, investment).
- **A clean, fast dashboard** showing balances, recent activity, and budget progress.
- **Predictions** of future expenses and account balances with confidence bands.
- **Recurring transactions** (salary, rent, subscriptions) auto-materialized into the ledger.
- **Budgets per category** with progress feedback on the dashboard.
- **Local-first**, single user, simple to deploy on free hosting tiers later.

Non-goals (v1): multi-user auth, multi-currency, bank integrations, receipt OCR, mobile apps.

## 2. Tech Stack & Rationale

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | As requested. |
| Web framework | **FastAPI** + Uvicorn | Async, fast, auto OpenAPI docs, great DX. |
| ORM | **SQLAlchemy 2.0** (sync) | Mature, simple for SQLite, ergonomic typed API. |
| Migrations | **Alembic** | Versioned schema changes. |
| Validation | **Pydantic v2** | Pairs with FastAPI; typed settings via `pydantic-settings`. |
| Templates | **Jinja2** | Server-rendered, no build step. |
| Interactivity | **HTMX** + **Alpine.js** | No bundler, no Node. Page-feels-instant. |
| Styling | **Tailwind CSS** (Play CDN for v1) | Utility-first, beautiful defaults, zero build. Compiled output planned for production. |
| Charts | **Chart.js** | Small (~70KB), good looking, simple API. |
| Forecasting | **pandas + numpy + statsmodels** | Lightweight stats. EMA + seasonality + linear trend. |
| Testing | **pytest** + **httpx** | Standard. |
| Lint/format | **ruff** | Fast, replaces flake8/black/isort. |
| Package mgmt | pyproject.toml + pip / uv | Modern. |

No Node.js, no React (in v1), no bundler. Easy to reason about; fast to develop.

## 3. Visual Design Tokens

A clean, neutral aesthetic. Minimal, Notion/Linear-ish. No shadows by default.

```text
Background: #fafafa (light) / #0a0a0a (dark)
Surface:    #ffffff / #171717
Border:     #e5e5e5 / #262626
Text:       #171717 / #fafafa
Muted:      #737373
Accent:     #4f46e5  (indigo-600)  - single accent
Positive:   #16a34a  (emerald-600) - income, in-budget
Negative:   #dc2626  (red-600)     - expense, over-budget

Font:       system-ui stack (no web fonts)
Radius:     rounded-lg (8px)
Shadow:     none by default; subtle on hover
```

Dark mode is implemented with Tailwind's `dark:` variant and an Alpine.js toggle persisted in `localStorage`.

## 4. Directory Layout

```
FutureFunds/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, mounts routers, static, templates
│   │   ├── config.py            # pydantic-settings
│   │   ├── database.py          # engine, SessionLocal, Base
│   │   ├── deps.py              # DI: get_db, get_current_user
│   │   ├── models/
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   ├── transaction.py
│   │   │   ├── recurring.py
│   │   │   └── budget.py
│   │   ├── schemas/             # Pydantic DTOs (added in later phases)
│   │   ├── crud/                # Pure DB functions (later phases)
│   │   ├── routers/
│   │   │   ├── pages.py
│   │   │   ├── accounts.py
│   │   │   ├── transactions.py
│   │   │   ├── categories.py
│   │   │   ├── budgets.py
│   │   │   ├── recurring.py
│   │   │   ├── dashboard.py
│   │   │   └── predictions.py
│   │   ├── services/
│   │   │   ├── forecasting.py
│   │   │   ├── recurring.py
│   │   │   └── analytics.py
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── dashboard.html
│   │   │   ├── accounts/  (list.html, form.html)
│   │   │   ├── transactions/  (list.html, form.html)
│   │   │   ├── categories/    (list.html, form.html)
│   │   │   ├── budgets/       (list.html, form.html)
│   │   │   ├── recurring/     (list.html, form.html)
│   │   │   └── partials/      (account_card, transaction_row, budget_bar, ...)
│   │   └── static/
│   │       ├── css/app.css
│   │       └── js/app.js
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
├── data/                        # SQLite file (gitignored)
├── scripts/
│   ├── seed.py
│   ├── dev.sh
│   ├── dev.ps1                  # Windows PowerShell
│   └── build_css.sh
├── .env.example
├── .gitignore
├── PLAN.md                      # this file
└── README.md
```

## 5. Database Schema (SQLite via SQLAlchemy)

### `accounts`

| Column           | Type        | Notes                                                |
|------------------|-------------|------------------------------------------------------|
| id               | INTEGER PK  |                                                      |
| name             | VARCHAR     | unique per user                                      |
| type             | ENUM        | `cash`, `bank`, `credit_card`, `savings`, `investment` |
| currency         | VARCHAR(3)  | ISO 4217                                             |
| opening_balance  | DECIMAL(18,2) | initial balance when account was added             |
| color            | VARCHAR     | hex; used in UI                                      |
| icon             | VARCHAR     | heroicon name                                        |
| is_active        | BOOLEAN     | soft-disable                                         |
| created_at       | DATETIME    |                                                      |
| updated_at       | DATETIME    |                                                      |

### `categories`

| Column     | Type        | Notes                                       |
|------------|-------------|---------------------------------------------|
| id         | INTEGER PK  |                                             |
| name       | VARCHAR     |                                             |
| type       | ENUM        | `expense`, `income`                         |
| color      | VARCHAR     |                                             |
| icon       | VARCHAR     |                                             |
| parent_id  | INTEGER FK  | self-FK to `categories.id` (nullable)       |

### `transactions`

| Column              | Type        | Notes                                                   |
|---------------------|-------------|---------------------------------------------------------|
| id                  | INTEGER PK  |                                                         |
| account_id          | INTEGER FK  | → `accounts.id`                                         |
| category_id         | INTEGER     | nullable; FK to `categories.id` added in Phase 5        |
| amount              | DECIMAL(18,2) | signed: +income, -expense                             |
| type                | ENUM        | `expense`, `income`, `transfer`                         |
| description         | VARCHAR     |                                                         |
| notes               | TEXT        | nullable                                                |
| date                | DATE        | the date the transaction occurred                       |
| transfer_pair_id    | INTEGER FK  | self-FK to `transactions.id` (nullable, for transfers)  |
| recurring_rule_id   | INTEGER     | nullable; FK to `recurring_rules.id` added in Phase 6   |
| created_at          | DATETIME    |                                                         |
| updated_at          | DATETIME    |                                                         |

Indexes: `(date)`, `(account_id, date)`.

**Transfers** are stored as two transactions (one negative, one positive) sharing a `transfer_pair_id`. This keeps the account ledger correct without a separate "transfer" table.

### `recurring_rules`

| Column               | Type        | Notes                                                  |
|----------------------|-------------|--------------------------------------------------------|
| id                   | INTEGER PK  |                                                        |
| account_id           | INTEGER FK  | → `accounts.id`                                        |
| category_id          | INTEGER FK  | → `categories.id`                                      |
| amount               | DECIMAL(18,2) |                                                      |
| type                 | ENUM        | `expense`, `income`                                    |
| description          | VARCHAR     |                                                        |
| frequency            | ENUM        | `daily`, `weekly`, `monthly`, `yearly`                 |
| interval             | INTEGER     | every N periods (default 1)                            |
| start_date           | DATE        |                                                        |
| end_date             | DATE        | nullable                                               |
| day_of_month         | INTEGER     | for monthly (1-31)                                     |
| day_of_week          | INTEGER     | for weekly (0=Mon .. 6=Sun)                            |
| last_generated_date  | DATE        | nullable                                               |
| is_active            | BOOLEAN     |                                                        |
| created_at           | DATETIME    |                                                        |
| updated_at           | DATETIME    |                                                        |

### `budgets`

| Column       | Type           | Notes                                       |
|--------------|----------------|---------------------------------------------|
| id           | INTEGER PK     |                                             |
| category_id  | INTEGER FK     | → `categories.id`                           |
| amount       | DECIMAL(18,2)  |                                             |
| period       | ENUM           | `weekly`, `monthly`, `yearly`               |
| start_date   | DATE           |                                             |
| is_active    | BOOLEAN        |                                             |
| created_at   | DATETIME       |                                             |
| updated_at   | DATETIME       |                                             |

## 6. Routes

### Page routes (HTML, server-rendered)

| Method | Path                          | Template                       |
|--------|-------------------------------|--------------------------------|
| GET    | `/`                           | `dashboard.html`               |
| GET    | `/accounts`                   | `accounts/list.html`           |
| GET    | `/accounts/new`               | `accounts/form.html` (new)     |
| GET    | `/accounts/{id}/edit`         | `accounts/form.html` (edit)    |
| GET    | `/transactions`               | `transactions/list.html`       |
| GET    | `/transactions/new`           | `transactions/form.html`       |
| GET    | `/categories`                 | `categories/list.html`         |
| GET    | `/budgets`                    | `budgets/list.html`            |
| GET    | `/recurring`                  | `recurring/list.html`          |

### HTMX form-submit routes (redirect to list page)

| Method | Path                          | Response                            |
|--------|-------------------------------|--------------------------------------|
| POST   | `/accounts`                   | `HX-Redirect: /accounts`            |
| PATCH  | `/accounts/{id}`              | `HX-Redirect: /accounts`            |
| DELETE | `/accounts/{id}`              | empty (200 OK, triggers refresh)     |
| POST   | `/transactions`               | `HX-Redirect: /transactions`        |
| PATCH  | `/transactions/{id}`          | `HX-Redirect: /transactions`        |
| DELETE | `/transactions/{id}`          | empty (200 OK, triggers refresh)     |
| POST   | `/categories`                 | `HX-Redirect: /categories`            |
| PATCH  | `/categories/{id}`            | `HX-Redirect: /categories`            |
| DELETE | `/categories/{id}`            | empty (200 OK, triggers refresh)       |
| POST   | `/budgets`                    | `HX-Redirect: /budgets`               |
| PATCH  | `/budgets/{id}`               | `HX-Redirect: /budgets`               |
| DELETE | `/budgets/{id}`               | empty (200 OK, triggers refresh)       |
| POST   | `/recurring`                  | `HX-Redirect: /recurring`             |
| PATCH  | `/recurring/{id}`             | `HX-Redirect: /recurring`             |
| DELETE | `/recurring/{id}`             | empty (200 OK, triggers refresh)       |

> POST/PATCH return `HX-Redirect` because the create/edit forms live on dedicated pages
> where the target element (`#account-list`, `#transaction-list`) does not exist.
> DELETE endpoints return 200 with `HX-Trigger: transaction-deleted` — the list page
> listens for this event and re-fetches the list.

### JSON API (used by Chart.js on the dashboard)

| Method | Path                                                   | Returns                  |
|--------|--------------------------------------------------------|--------------------------|
| GET    | `/api/transactions`                                    | list (filterable)        |
| GET    | `/api/transactions/{id}`                               | single transaction       |
| GET    | `/api/categories`                                      | list of categories       |
| GET    | `/api/categories/{id}`                                 | single category          |
| GET    | `/api/budgets`                                         | list of budgets          |
| GET    | `/api/budgets/{id}`                                    | single budget            |
| GET    | `/api/recurring`                                       | list of rules            |
| GET    | `/api/recurring/{id}`                                  | single rule              |
| GET    | `/api/recurring/{id}/preview`                          | next 5 occurrences       |
| POST   | `/api/recurring/materialize`                           | trigger materialization  |
| GET    | `/api/accounts/{id}/balance`                           | account balance          |
| GET    | `/api/dashboard/summary?year=&month=&start_date=&end_date=` | monthly totals (date-range filterable) |
| GET    | `/api/dashboard/spending?range=30d&start_date=&end_date=`  | daily expense series     |
| GET    | `/api/dashboard/category-breakdown?month=YYYY-MM&start_date=&end_date=` | category totals |
| GET    | `/api/dashboard/budgets?month=YYYY-MM&start_date=&end_date=`  | budget progress          |
| GET    | `/api/accounts/{id}/balance-history?range=90d`         | daily balance series     |
| GET    | `/api/predictions/expenses?horizon=30`                 | 7/30-day forecast + band |
| GET    | `/api/predictions/balance?horizon=90`                  | projected balance + band |
| GET    | `/api/budgets/status?month=YYYY-MM`                    | per-category progress    |

OpenAPI docs are auto-generated at `/docs` and `/redoc` for the JSON API.

## 7. Forecasting Algorithm

Lightweight statistics, no deep learning. Runs on CPU in milliseconds.

### Daily expense forecast (horizon H days)

1. Build a daily series `S` from the last `FORECAST_HISTORY_DAYS` (default 180) of expense transactions.
2. **Trend**: `T(t) = EMA(S, alpha=0.3)` - exponential moving average with smoothing factor 0.3.
3. **Seasonality**: for each weekday `w`, `seasonal[w] = mean(S[weekday=w]) - mean(S)` (day-of-week effect).
4. **Residuals**: `R(t) = S(t) - T(t) - seasonal[weekday(t)]`.
5. `residual_std = std(R)`.
6. For each future day `t` in `[now, now+H]`:
   - `forecast(t) = T(now) + seasonal[weekday(t)]`
   - `band(t) = ±1.96 * residual_std`  (≈ 95% confidence interval)
7. Cache key: `(scope, horizon, today)`. TTL: `FORECAST_CACHE_TTL_SECONDS` (default 300s).

### Per-category forecast

Same as above applied per category, weighted toward recent days via EMA.

### Balance projection (per account, horizon H days)

```
future_income(t)  = forecast of income + materialized recurring income up to t
future_expense(t) = forecast of expense + materialized recurring expense up to t
projected_balance(t) = current_balance
                       + Σ future_income(0..t)
                       - Σ future_expense(0..t)
```

### Runway (warning chip on dashboard)

`earliest t where projected_balance(t) ≤ 0`, else `null`. Surfaced as "⚠ X days until projected zero" if non-null and within 90 days.

## 8. Recurring Rules Engine

- **Materializer**: walks all active `recurring_rules` and creates any missed transactions since `last_generated_date` (or `start_date` if null).
- **Idempotent**: never duplicates; updates `last_generated_date` after each successful pass.
- **Triggers**:
  - FastAPI startup event (if `RECURRING_AUTO_MATERIALIZE=true`).
  - Manual `POST /api/recurring/materialize` endpoint.
- **Preview**: "Next 5 occurrences" computed in Python without writing to the DB.

## 8.1 Phase 8 — Polish (detailed tasks)

The following items are tracked for Phase 8 based on code review findings:

| # | Task | Status |
|   |------|--------|
| 1 | **Dashboard period filter** | ✅ done |
| 2 | **Seed script hardening** | ✅ done |
| 3 | **Test count documentation sync** | ✅ done |
| 4 | **Datepicker dark-mode fix** | ✅ done |
| 5 | **Error pages** | ✅ done |
| 6 | **Accessibility pass** | ✅ done |
| 7 | **Compiled Tailwind CSS** | ✅ done |
| 8 | **Free-hosting deploy notes** | ✅ done |
| 9 | **Shared palette constant** | ✅ done |
| 10 | **Account balance display fix** | ✅ done |
| 11 | **Currency symbol encoding fix** | ✅ done |
| 12 | **Seed recurring rules** | ✅ done |
| 13 | **Mobile hamburger navigation** | ✅ done |

## 9. Phased Roadmap

| # | Phase | Deliverable | Checkpoint |
|---|---|---|---|---|
| 1 | **Foundation** | Scaffold, FastAPI app, `config.py` with `DEFAULT_CURRENCY="INR"`, base template (Tailwind/HTMX/Alpine/Chart.js, dark-mode toggle), Alembic initialized, `.env.example`, `.gitignore`, `PLAN.md`, README, `dev.ps1`/`dev.sh` | `uvicorn` serves styled dashboard at <http://127.0.0.1:8000> |
| 2 | **Accounts** | `Account` model + migration, CRUD pages, HTMX form partials, validation, color/icon per account | Create cash + bank + credit card; balances on placeholder dashboard |
| 3 | **Transactions** | **done** | Ledger, transfers, filterable list, 47 tests |
| 4 | **Dashboard v1** | **done** | `services/analytics.py`, `/api/dashboard/*`, real Chart.js charts (daily-spend bar, category donut), monthly KPI cards, 18 tests |
| 4.1 | **Quick-add (redirect)** | Primary `+ Add transaction` button on the dashboard linking to `/transactions/new`; form's `next` query param threaded through so a successful create redirects back to `/` if invoked from the dashboard | Click button on dashboard, submit form, land back on dashboard with refreshed data |
| 5 | **Categories & Budgets** | **done** | `Category`, `Budget` models + migrations, CRUD pages, budget progress bars on dashboard, 45 tests (21 categories + 24 budgets) |
| 6 | **Recurring rules** | **done** | `RecurringRule` model + migration, `services/recurring.py` materializer, auto-run on startup, "next 5 occurrences" preview, 36 tests |
| 7 | **Predictions** | **done** | `services/forecasting.py`, `/api/predictions/*`, balance projection chart w/ confidence band, 7/30-day expense forecast, runway warning, 22 tests |
| 8 | **Polish** | **done** | Dashboard period filter, seed hardening, error pages, a11y, compiled Tailwind, deploy notes — **202 tests total** |

> Note: `scripts/seed.py` was implemented ahead-of-schedule (post-Phase 3 bugfix session).
> It creates 4 accounts + 11 transaction rows with realistic INR amounts using Alembic.

> Note: Dashboard chart colours use the design tokens from §3 (`accent-600` = `#4f46e5` for bars, `positive-600` = `#16a34a` / `negative-600` = `#dc2626` for category labels). Colours are defined via `window.FF_COLORS` in `js/app.js` and consumed in `dashboard.html`.

## 10. Local Dev Workflow

### First time

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head
```

### Daily

```bash
# from project root
scripts\dev.ps1         # Windows
# or
./scripts/dev.sh        # macOS/Linux
```

Then open <http://127.0.0.1:8000>.

## 11. Free Hosting Notes (future)

The app is a single FastAPI process + a SQLite file. Free hosting options that work:

- **Render** free tier - web service, persistent disk for SQLite.
- **Railway** free tier - similar; ephemeral disk is the main risk.
- **Fly.io** free tier - small VM with persistent volume.

The `Dockerfile` at the project root packages the app for any container-based host. See `README.md` §Deployment for platform-specific guidance.

## 12. Future-Proofing (no work now, but design allows it)

- **Multi-user**: add a `users` table and `user_id` FK on every model; switch `deps.get_current_user` from no-op to real session auth.
- **Multi-currency**: per-account `currency` is already in the schema; just add an FX rate cache and conversion in the analytics layer.
- **Import / receipts**: `attachments` table; HTMX file upload is trivial with the existing stack.
- **Production CSS**: switch from Tailwind Play CDN to compiled `app.compiled.css` via `scripts/build_css.sh` (uses `backend/tailwind.config.js`). Already set up; just needs the Tailwind standalone CLI on PATH.
- **Quick-add transaction modal on the dashboard** — currently the dashboard links to the full `/transactions/new` page. A future enhancement would add an Alpine.js modal that lazy-loads the form via `hx-get="/transactions/new?partial=1"`, submits in place, and refreshes dashboard widgets (KPIs, charts, account balances, recent transactions) via HTMX partial swaps. The form would be extracted into `partials/transaction_form.html` so the same partial is reused by the modal and the full create page.

## 13. Open Considerations

- Tagging on transactions (e.g. `#business`)? Defer to v2 unless requested.
- Net-worth tracking across investment accounts? Track in `accounts` table; no separate net-worth model needed.
- "Shared" expenses (split with a partner)? Out of scope for v1.
- Mobile responsiveness - hamburger menu for navigation added; deep mobile UX in a future pass.

## 14. Changelog

### Phase 1 — Foundation (complete)

Shipped:
- Project scaffold (`backend/app/`, `data/`, `scripts/`) with `.gitignore`, `.env.example`, `pyproject.toml`, `requirements.txt`.
- `app/config.py` (pydantic-settings, reads `.env`, exposes `default_currency="INR"`, `currency_symbol="₹"`).
- `app/database.py` (SQLAlchemy 2.0 engine, `SessionLocal`, `Base`, `get_db`, `session_scope`, `ensure_data_dir`).
- `app/main.py` (FastAPI app, lifespan that ensures data dir, static mount, Jinja2 templates, global template context, `GET /`, `GET /healthz`).
- `app/templates/base.html` - clean neutral theme (slate/indigo), Tailwind Play CDN with inline config (single accent `accent-600` = indigo-600, `positive-600` = emerald-600, `negative-600` = red-600), system font stack, HTMX 1.9, Alpine.js 3, Chart.js 4, dark-mode toggle persisted in `localStorage`, SVG favicon, sticky header with phase-aware nav, footer with `/docs` link.
- `app/templates/dashboard.html` - placeholder dashboard with 4 KPI cards, 2 chart placeholders, recent-transactions placeholder, and an 8-phase build-status panel.
- Alembic initialized: `alembic.ini`, `alembic/env.py` (loads `Base.metadata` from `app.database`, `render_as_batch=True` for SQLite ALTER support), `alembic/script.py.mako`.
- `scripts/dev.ps1` (Windows) and `scripts/dev.sh` (POSIX) - one-shot launchers that create venv, install deps, run migrations, and start uvicorn with `--reload`.
- `scripts/build_css.sh` (placeholder for future compiled Tailwind).
- `tests/conftest.py` (in-memory SQLite + `TestClient`), `tests/test_smoke.py` (3 passing tests).
- `PLAN.md` (this file) and `README.md`.

Verified:
- `pip install -e ".[dev]"` succeeds on Python 3.14.4.
- `alembic upgrade head` is a clean no-op (creates `alembic_version` table, no rows).
- `uvicorn app.main:app` boots; `GET /` returns 200 with "FutureFunds" and "Dashboard" rendered; `GET /healthz` returns `{"status":"ok","app":"FutureFunds"}`; `GET /static/css/app.css` returns 200 with `text/css`.
- `pytest`: 3/3 passing (health, dashboard render, static CSS).

Deviations from the original scaffold: `pyproject.toml` had to drop the `readme = "../README.md"` line because setuptools refuses paths outside the package directory. The README is still referenced from the project root, just not from the package metadata. This is a packaging-time concern only; runtime is unaffected.

### Phase 2 — Accounts (complete)

Shipped:
- `app/models/account.py`, `app/schemas/account.py`, `app/crud/account.py` — full Account model with `AccountType` enum (cash, bank, credit_card, savings, investment), Pydantic DTOs (`AccountCreate`, `AccountUpdate`, `AccountRead`), CRUD helpers (`list`, `get`, `create`, `update`, `delete`, `compute_balance`).
- Alembic migration `1c807833bf32` — creates `accounts` table. Applied.
- `app/templates.py` — shared `Jinja2Templates` module extracted from `main.py` for router reuse.
- `app/routers/pages.py` — `GET /` dashboard with real balance + per-account cards + empty state + build-status panel.
- `app/routers/accounts.py` — 3 HTML pages, 3 HTMX mutation endpoints, 3 JSON API endpoints. Form data via `Form()`, PATCH with `Optional[Form(None)]` + filtered dict to avoid NOT NULL violations.
- Templates: `accounts/list.html`, `accounts/form.html` (create/edit shared), `partials/account_card.html`. HTMX cards with edit/delete (confirmation dialog).
- `app/templates/base.html` — "Accounts" nav active.
- `tests/test_accounts.py` — 20 tests (15 with client, 5 CRUD with db_session). All pass.
- `tests/conftest.py` — refactored to use temp file-based SQLite (TestClient + in-memory per-connection issue).
- `pyproject.toml` — added `python-multipart`.

Verified: 25 tests passing, all pages returning 200, full CRUD round-trip via HTMX.

### Phase 4 — Dashboard v1 (complete)

Shipped:
- `app/services/analytics.py` — analytics service with `monthly_summary`, `daily_spending`, `category_breakdown`, and `balance_history` functions. All return structured dicts/lists for the dashboard JSON API.
- `app/routers/dashboard.py` — 4 JSON API endpoints:
  - `GET /api/dashboard/summary?year=&month=` — monthly income, expense, net, savings rate
  - `GET /api/dashboard/spending?range=30` — daily expense bar chart data
  - `GET /api/dashboard/category-breakdown?month=YYYY-MM` — breakdown by type (placeholder until categories exist in Phase 5)
  - `GET /api/accounts/{id}/balance-history?range=90` — daily running balance per account
- `app/main.py` — dashboard router mounted
- `app/templates/dashboard.html` — placeholder KPI values replaced with `id`-annotated elements updated client-side via `fetch()`; two `<canvas>` elements for Chart.js (daily spending bar chart, category doughnut chart); build status Phase 4 now green; `{% block scripts %}{% endblock %}` appended to the page.
- `app/templates/base.html` — added `{% block scripts %}{% endblock %}` slot at the end of `<body>`; footer updated from "Phase 3" to "Phase 4".
- `tests/test_dashboard.py` — 16 tests covering all analytics functions and HTTP endpoints.

Key decisions during implementation:
- Charts are initialized in a `DOMContentLoaded` listener so all deferred scripts (Alpine.js, Chart.js) are guaranteed available before `new Chart(...)` is called.
- All monetary amounts are returned as strings from the API (to preserve SQLite `Numeric` precision) and `parseFloat()`-ed client-side.
- `category_breakdown` groups by transaction type as a fallback; when the `categories` table is added in Phase 5, it should be updated to group by `Transaction.category_id` with proper labels.

Verified:
- `pytest -q` → **89 passed** (3 smoke + 24 accounts + 7 config + 39 transactions + 16 dashboard).
- `GET /api/dashboard/summary` returns correct monthly totals.
- `GET /api/dashboard/spending?range=7` returns 7 daily entries with proper amounts.
- Dashboard page renders canvas elements with `id="spending-chart"` and `id="category-chart"`.
- KPI cards show real data after client-side fetch completes.

### Phase 4.1 — Quick-add transaction (redirect) (complete)

Shipped:
- `backend/app/templates/dashboard.html` — primary `+ Add transaction` button in the page header; links to `/transactions/new?from=/`.
- `backend/app/routers/transactions.py` — `GET /transactions/new` accepts optional `?from=<path>`; `POST /transactions` accepts a `next` form field and returns `HX-Redirect: <next>` for safe local paths (falls back to `/transactions` on missing/invalid input). New `_safe_next` helper enforces same-origin policy (rejects `//evil.com`, `http://...`, `javascript:`).
- `backend/app/templates/transactions/form.html` — hidden `next` input; "Cancel" link now respects `next_url`.
- `backend/tests/test_transactions.py` — 7 new tests (button presence, `?from=/` query param, hidden `next` input, default value, custom redirect, fallback redirect, open-redirect guard).

Verified:
- `pytest -q` → **141 passed** (134 + 7 new).
- Dashboard renders a primary CTA linking to `/transactions/new?from=/`.
- `GET /transactions/new?from=/` then POST → browser lands on `/` after save.
- Open-redirect attempts (`//evil.com`, `http://evil.com`, `javascript:alert(1)`) are rejected and fall back to `/transactions`.
- ruff clean.

Future enhancement (deferred): quick-add modal — see §12.

### Phase 5 — Categories & Budgets (complete)

Shipped:
- `app/models/category.py` — `Category` ORM model with `CategoryType` enum (expense/income), nullable self-FK `parent_id`, color, icon.
- `app/models/budget.py` — `Budget` ORM model with `BudgetPeriod` enum (weekly/monthly/yearly), FK to `categories.id`, decimal `amount`, `start_date`, `is_active`, `TimestampMixin`.
- `app/models/transaction.py` — `category_id` column updated from plain `Integer` to `ForeignKey("categories.id")` with `category` relationship.
- `app/models/__init__.py` — imports `Budget`, `BudgetPeriod`, `Category`, `CategoryType`.
- Alembic migration `2a9b3c7def01` — creates `categories` and `budgets` tables; adds FK constraint on `transactions.category_id`.
- `app/schemas/category.py` — `CategoryCreate`, `CategoryUpdate`, `CategoryRead` Pydantic DTOs.
- `app/schemas/budget.py` — `BudgetCreate`, `BudgetUpdate`, `BudgetRead` Pydantic DTOs.
- `app/schemas/transaction.py` — `TransactionCreate` and `TransactionUpdate` now include optional `category_id`.
- `app/crud/category.py` — `list_categories` (with optional type filter), `get_category`, `create_category` (defaults color to purple), `update_category`, `delete_category` (blocks if has transactions).
- `app/crud/budget.py` — `list_budgets` (with optional active-only filter), `get_budget`, `create_budget`, `update_budget`, `delete_budget`.
- `app/crud/transaction.py` — `create_transaction` accepts optional `category_id` param.
- `app/routers/categories.py` — 3 HTML pages (`/categories`, `/categories/new`, `/categories/{id}/edit`), 3 HTMX mutation endpoints (POST/PATCH/DELETE), 2 JSON API endpoints (`GET /api/categories`, `GET /api/categories/{id}`).
- `app/routers/budgets.py` — 3 HTML pages (`/budgets`, `/budgets/new`, `/budgets/{id}/edit`), 3 HTMX mutation endpoints (POST/PATCH/DELETE), 2 JSON API endpoints (`GET /api/budgets`, `GET /api/budgets/{id}`). Budget list page renders real-time progress bars with spent/remaining data.
- `app/services/analytics.py` — `category_breakdown` updated to group by real `Category` (falls back to type-based grouping when no categories are assigned); `budget_progress` added (returns per-budget spend percentage, remaining, over-budget flag).
- `app/routers/dashboard.py` — new `GET /api/dashboard/budgets` endpoint returns budget progress data for the dashboard.
- Templates: `categories/list.html`, `categories/form.html`, `budgets/list.html`, `budgets/form.html`, `partials/category_card.html`, `partials/budget_card.html` (with inline progress bar).
- `app/templates/base.html` — "Categories" nav link added next to "Transactions"; "Budgets" nav link enabled; footer updated to "Phase 5".
- `app/templates/dashboard.html` — budget progress section added (client-side rendered from `/api/dashboard/budgets` with progress bars); category doughnut chart uses per-item colors from the API; Phase 5 build status green.
- `app/main.py` — mounts `categories_router` and `budgets_router`.
- `tests/test_categories.py` — 21 tests: enum values, CRUD operations, 3 HTML page tests, 3 HTMX mutation tests, 3 JSON API tests, 2 validation failure tests. All pass.
- `tests/test_budgets.py` — 24 tests: enum values, CRUD operations, 3 budget_progress scenarios (no data, with spending, over budget, ignores inactive), 4 HTML page tests, 3 HTMX mutation tests, 3 JSON API tests, 2 validation failure tests, 1 dashboard endpoint test. All pass.

Key decisions during implementation:
- `category_breakdown` groups by real categories when transactions have them assigned; falls back to type-based grouping for backward compatibility.
- Budget progress is computed on-the-fly from transactions (not stored) — sums expenses per category within the current period.
- Budget cards on the budget list page show a computed progress bar with spent amount, percentage, remaining, and over-budget detection.
- Dashboard budget progress is fetched client-side from `/api/dashboard/budgets` and rendered with inline HTML (no Chart.js needed for progress bars).

Verified:
- `pytest -q` → **134 passed** (3 smoke + 24 accounts + 21 categories + 24 budgets + 7 config + 16 dashboard + 39 transactions).
- `GET /categories` renders category list with empty state and "Add category" CTA.
- `GET /budgets` renders budget list with progress bars computed from live transaction data.
- `GET /api/dashboard/budgets` returns budget progress JSON with correct spent/percentage/remaining.
- `GET /api/dashboard/category-breakdown` now returns category names and colors when categories are assigned.
- `GET /` renders budget progress section with `id="budget-section"` and `id="budget-progress-container"`.
- Full CRUD round-trip for categories and budgets via HTMX.
- ruff clean.

### Phase 3 — Transactions (complete)

Shipped:
- `app/models/transaction.py` — `Transaction` ORM model with `TransactionType` enum (expense/income/transfer), signed `amount`, FKs to `accounts.id` and self-FK `transfer_pair_id`, nullable `category_id`/`recurring_rule_id` (FK constraints deferred to Phases 5 & 6).
- Alembic migration `50a1b87ac679` — creates `transactions` table with indexes on `(date)` and `(account_id, date)`. Applied.
- `app/schemas/transaction.py` — `TransactionCreate`, `TransactionUpdate`, `TransactionRead`, `TransferCreate` Pydantic DTOs.
- `app/crud/transaction.py` — `list_transactions` (filterable by account/type/date range/description), `get_transaction`, `create_transaction`, `update_transaction`, `delete_transaction`, `create_transfer` (two rows sharing `transfer_pair_id`), `compute_account_balance` (sums transactions), `get_recent_transactions`.
- `app/crud/account.py` — `compute_balance` updated to delegate to `compute_account_balance` (real balance = opening + transaction sum).
- `app/routers/transactions.py` — 3 HTML pages (`/transactions`, `/transactions/new`, `/transactions/{id}/edit`), 3 HTMX mutation endpoints (POST/PATCH/DELETE), 2 JSON API endpoints (`GET /api/transactions`, `GET /api/transactions/{id}`). Form data via `Form()`, transfer flow handled via `from_account_id`/`to_account_id` fields.
- Templates: `transactions/list.html` (filter form with account/type/date range/search + transaction list), `transactions/form.html` (create/edit shared, JS toggles between single account and from/to account fields for transfers), `partials/transaction_row.html` (type icon, description, amount, date, edit/delete actions), `partials/transaction_list_items.html` (list of rows or empty state, reused by HTMX filter partial swaps).
- Dashboard: recent-transactions placeholder replaced with real list of last 10 transactions. Account card balances now use computed balances (opening + transactions). Phase 3 status indicator green.
- `app/main.py` — mounts `transactions_router`.
- `app/templates/base.html` — "Transactions" nav link active. Footer updated to "Phase 3".
- `tests/test_transactions.py` — 29 tests: model enum values, CRUD operations, filtered listing, balance computation, transfer creation with balance consistency, 3 HTML page tests, 4 HTMX mutation tests, 2 JSON API tests, 4 validation failure tests. All pass.

Key decisions during implementation:
- `amount` is stored signed (+income, -expense). Form input is always positive; the router applies the sign based on `type`.
- Transfers are created via a single form submission with `from_account_id` and `to_account_id`; the backend creates both rows in a single request.
- `category_id` and `recurring_rule_id` are plain nullable `Integer` columns (no FK constraint) until their respective tables exist in later phases.
- Amount validation (`> 0`) is done in the router layer, not in the Pydantic schema, because form data bypasses schema validation.

Verified:
- `pytest -q` → **54 passed** (3 smoke + 20 accounts + 2 helpers + 29 transactions).
- `GET /` renders dashboard with real recent transactions, computed balances, build status (Phase 1-3 green).
- `GET /transactions` renders filter form + empty state. `GET /transactions/new` renders form with account dropdown and transfer toggle.
- `GET /healthz` returns `{"status":"ok","app":"FutureFunds"}`.
- Full CRUD round-trip: create expense → see row → edit description → row updates → delete → row removed (via HTMX).
- Create transfer from account A to B → both balances reflect correctly.

#### Post-Phase 3 bugfixes (this session)

**HTMX form redirect**: POST/PATCH on both accounts and transactions originally returned
`partials/account_card.html` / `partials/transaction_row.html` targeted at `#account-list` /
`#transaction-list`. But the form pages (`/accounts/new`, `/transactions/{id}/edit`, etc.)
are dedicated full-page views — those target elements do not exist in those pages, so HTMX
silently discarded the response ("nothing happens"). **Fix**: POST/PATCH now return
`Response(headers={"HX-Redirect": "/accounts"})` (or `/transactions`). The `hx-target`
and `hx-swap` attributes were removed from the form templates. Tests updated to use the
JSON API to look up created entities instead of parsing response HTML.

**DELETE route accidentally eaten**: During the HTMX redirect refactor of
`transactions.py`, the `@router.delete("/transactions/{transaction_id}")` endpoint was
accidentally included in the edit's `oldString` and deleted. Restored it to its original
logic (200 + `HX-Trigger: transaction-deleted`).

**Filter 422 on empty string**: The `/transactions` and `/api/transactions` routes
declared `account_id: int | None = Query(None, alias="account")`. When the HTML form
submitted `account=` (empty string), FastAPI/Pydantic v2 rejected it with 422 because
`""` cannot be parsed as `int`. **Fix**: changed to `str | None` with manual
`try: int(account_id)` parsing — empty strings become `None`, valid numbers pass through.

**Account checkbox not saving**: The account edit form has an `is_active` checkbox.
When unchecked, HTML sends **no value** for it; FastAPI used the default `Form(None)`,
and the `if is_active is not None:` guard skipped the field entirely. **Fix**: added
`<input type="hidden" name="is_active" value="false" />` after the checkbox. The hidden
field always submits `"false"`; when checked, the checkbox value `"true"` arrives first
in the form data, so `Form()` correctly receives `"true"`. Unchecked → only the hidden
`"false"` is sent.

**Seed script upgraded**: `scripts/seed.py` was rewritten from a placeholder to a real
seeder that creates 4 accounts (Wallet, HDFC Bank, SBI Savings, Axis Credit Card) with
₹ amounts and 11 transaction rows (salary, rent, transfer, groceries, bills, etc.).
It runs `alembic upgrade head` programmatically via `_ensure_migrations()` rather than
`Base.metadata.create_all()`, avoiding migration conflicts with `dev.ps1`.

### Phase 6 — Recurring rules (complete)

Shipped:
- `app/models/recurring.py` — `RecurringRule` ORM model with `RecurringFrequency` enum (daily/weekly/monthly/yearly), FK to `accounts.id` and `categories.id`, `last_generated_date` idempotency key, `TimestampMixin`.
- `app/models/transaction.py` — `recurring_rule_id` changed from plain `Integer` to `ForeignKey("recurring_rules.id")`, `recurring_rule` relationship added.
- `app/models/__init__.py` — imports `RecurringFrequency`, `RecurringRule`.
- Alembic migration `fb627ac5984d` — creates `recurring_rules` table; adds FK constraint on `transactions.recurring_rule_id`.
- `app/schemas/recurring.py` — `RecurringRuleCreate`, `RecurringRuleUpdate`, `RecurringRuleRead` Pydantic DTOs.
- `app/crud/recurring.py` — `list_rules` (with active-only filter), `get_rule`, `create_rule`, `update_rule`, `delete_rule`, `update_last_generated_date`.
- `app/services/recurring.py` — `materialize_rule` (creates missed transactions for a single rule), `materialize_all` (processes all active rules), `next_occurrences` (preview without writing to DB). Materializer is idempotent — never duplicates, updates `last_generated_date` after each pass.
- `app/routers/recurring.py` — 3 HTML pages (`/recurring`, `/recurring/new`, `/recurring/{id}/edit`), 3 HTMX mutation endpoints (POST/PATCH/DELETE), 2 JSON API endpoints (`GET /api/recurring`, `GET /api/recurring/{id}`), preview endpoint (`GET /api/recurring/{id}/preview`), materialize endpoint (`POST /api/recurring/materialize`).
- Templates: `recurring/list.html` (grid with next-occurrence preview), `recurring/form.html` (shared create/edit, JS toggles day-of-month/week fields by frequency), `partials/recurring_card.html` (with inline preview, category badge, inactive badge).
- `app/main.py` — mounts `recurring_router`; lifespan now calls `materialize_all()` on startup when `RECURRING_AUTO_MATERIALIZE=true`.
- `app/templates/base.html` — "Recurring" nav link enabled; footer updated to "Phase 6".
- `app/templates/dashboard.html` — Phase 6 build status green.
- `tests/test_recurring.py` — 47 tests: model enum, CRUD, `next_occurrences` (all frequencies + edge cases), materialize (with idempotency verification), HTML pages, HTMX mutations, JSON API, preview/materialize endpoints, validation. All pass.

Key decisions during implementation:
- The `type` field on `RecurringRule` is a plain `String(10)` column (not an enum) for simplicity; validated at the router layer.
- Form fields (`is_active`, `day_of_month`, `day_of_week`) use `str | None = Form(None)` with manual parsing to avoid FastAPI coercion issues with HTML empty-string submissions (same pattern as the Phase 3 `account_id` filter fix).
- `_next_date` helper uses interval-based arithmetic: adds `interval` periods to `after`, then snaps to the configured `day_of_week`/`day_of_month` if set.
- Auto-materialize on startup is controlled by `RECURRING_AUTO_MATERIALIZE` (default `true`).

Verified:
- `pytest -q` → **181 passed** (134 existing + 47 recurring).
- `GET /recurring` renders list with empty state and "Add rule" CTA.
- `GET /recurring/new` renders form with account/category dropdowns, frequency selector, conditional day fields.
- Full CRUD round-trip for recurring rules via HTMX (create → edit → delete).
- `GET /api/recurring/{id}/preview` returns next 5 occurrence dates.
- `POST /api/recurring/materialize` creates transaction rows for all active rules and returns counts.
- Materialize is idempotent — second call produces 0 new transactions.
- Inactive rules are skipped by `materialize_all`.
- `ruff check .` — all clean.

### Phase 7 — Predictions (complete)

Shipped:
- `app/services/forecasting.py` — forecasting engine with EMA (exponential moving average), day-of-week seasonality decomposition, confidence bands (95%, z=1.96), and runway detection. Exposes `expense_forecast()` and `balance_projection()`. Simple in-memory cache with TTL from `FORECAST_CACHE_TTL_SECONDS`.
- `app/routers/predictions.py` — two JSON API endpoints: `GET /api/predictions/expenses?horizon=30` (daily expense forecast with upper/lower confidence bands) and `GET /api/predictions/balance?horizon=90` (projected total balance with confidence bands and runway date).
- `app/main.py` — `predictions_router` wired in.
- `app/templates/dashboard.html` — balance projection line chart (Chart.js with filled confidence band), runway warning chip (amber alert in total balance KPI card, shows "X days until projected zero"), Phase 7 build status green.
- `app/templates/base.html` — footer updated to "Phase 7".
- `tests/test_predictions.py` — 41 tests covering: EMA computation, seasonal factors, daily series, decomposition, empty-data edge cases, expense forecast, balance projection, runway detection, HTTP endpoints, dashboard UI elements.

Key decisions:
- Cache keyed by `(scope, horizon, today)` with configurable TTL.
- Balance projection combines income and expense forecasts with combined residual std for confidence bands.
- Runway suppressed when `current_balance <= 0`.
- `_daily_series` uses `func.abs()` to handle signed DB amounts.
- Chart.js balance chart uses three datasets (upper fill, line, lower fill) to render the confidence interval as a shaded area.

Verified:
- ✅ `pytest -q` → **222 passed** (181 existing + 41 new).
- ✅ All prediction endpoints return correct structure with upper/lower bands.
- ✅ Dashboard renders balance chart, runway warning, Phase 7 green.
- ✅ `ruff check .` — all clean.

### Phase 8 — Polish (complete)

Shipped:
- **Dashboard period filter**: Added `<select#period-select>` with 5 options (Current month, Previous month, Last 3 months, This year, All time). New `_resolve_date_range()` helper in `analytics.py`. All analytics functions accept optional `start_date`/`end_date` params. Dashboard JS refactored to `loadAllData(period)` with chart destroy/re-create.
- **Seed script hardening**: `scripts/seed.py` `_ensure_migrations()` tries `alembic upgrade head` → `stamp head` → delete `data/expenses.db` as last resort.
- **Test count doc sync**: Updated PLAN.md, STATUS.md, README.md to show 202 tests. Footer → "Phase 8".
- **Datepicker dark-mode fix**: Moved `color-scheme: dark` and `::-webkit-calendar-picker-indicator` from inline `<style>` to `app.css`. Added `::-webkit-datetime-edit { color: inherit }`. Removed the inline `<style>` block.
- **Error pages**: `404.html` and `500.html` templates extending `base.html`. Handlers `@app.exception_handler(404)` and `@app.exception_handler(Exception)` in `main.py`.
- **Accessibility pass**: `aria-label` on all edit/delete links/buttons. `aria-hidden="true"` on decorative SVGs. `role="img"` + `aria-label` on 3 canvases. `role="alert"` on runway warning and form error container. `for` + `aria-describedby` on colour inputs. Nav and theme toggle labelled.
- **Compiled Tailwind CSS**: `backend/tailwind.config.js` mirroring inline config. `scripts/build_css.sh` updated with `--config` flag.
- **Free-hosting deploy notes**: `Dockerfile` at project root. Deployment section in README with Render/Railway/Fly.io guidance.
- **Shared palette constant**: `window.FF_COLORS` moved from `base.html` to `js/app.js`.
- **Account balance display fix**: `accounts/list.html` now passes `balance` per-account via `{% with balance = balances[account.id] %}` before including `partials/account_card.html`, matching dashboard behavior.
- **Currency symbol encoding fix**: Changed `config.py` default from literal `₹` to Unicode escape `\u20b9` to prevent Windows encoding corruption. Updated `.env.example` accordingly.
- **Seed recurring rules**: `scripts/seed.py` now creates 2 sample `RecurringRule` entries (Monthly Salary income, Monthly Rent expense) and deletes existing rules in `_clean()` for idempotent re-seeding.
- **Mobile hamburger navigation**: Added responsive hamburger menu to `base.html` with Alpine.js toggle. Visible only below `md` breakpoint. Animated slide-down panel, click-outside to close, ARIA accessible attributes. Desktop nav unchanged.

Key decisions:
- Dashboard period filter uses `start_date`/`end_date` API params for multi-month ranges; single-month periods still use `year`/`month` for backward compat.
- Budget progress with explicit dates ignores per-period bounds and aggregates over the full range.
- Seed script deletes DB file only as last resort (synthetic data is safe to lose).
- `FF_COLORS` defined in `js/app.js` (loaded before chart initialization).

Verified:
- ✅ `pytest -q` → **202 passed** (test suite adjusted for API response format changes in dashboard endpoints).
- ✅ `ruff check .` — all clean.
- ✅ Dashboard filter cycles through all periods without JS errors.
- ✅ Seed script recovers from stale/already-migrated DB.
- ✅ `GET /nonexistent` returns styled 404; unhandled errors return styled 500.
- ✅ All accessibility attributes present in rendered HTML.
- ✅ `tailwindcss` CLI compiles with the new config when available.
- ✅ `Dockerfile` builds and serves the app.
- ✅ `window.FF_COLORS` accessible from dashboard chart configs.
