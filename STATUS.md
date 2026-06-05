# FutureFunds — Project Status (handoff snapshot)

> **Read this first if you're a new agent/session/model.** It captures *where the project is right now* and the minimum context needed to continue. For full design rationale see [`PLAN.md`](./PLAN.md). For setup & usage see [`README.md`](./README.md).

Last updated: end of **Phase 5 (Categories & Budgets)** — Phase 6 (Recurring rules) is next.

---

## 1. Project identity

| Field | Value |
|---|---|
| **Name** | FutureFunds (personal expense tracker) |
| **Repo root** | `E:\Repos\future-funds\` (this directory) |
| **Backend** | `backend/` (FastAPI app) |
| **Stack** | Python 3.11+ (verified on 3.14.4), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pydantic-settings, Jinja2, HTMX 1.9, Alpine.js 3, Tailwind CSS (Play CDN for v1), Chart.js 4, pandas + numpy + statsmodels, pytest, ruff |
| **Database** | SQLite at `data/expenses.db` (gitignored) |
| **Default currency** | `INR` (display symbol `₹`), single currency, configurable via `.env` |
| **Mode** | Local-first, single user. Future-proofed for multi-user / free-host deploy. |
| **Theme** | Clean neutral slate/indigo, light + dark (persisted in `localStorage`) |

---

## 2. Build status

| # | Phase | Status | Notes |
|---|---|---|---|
| 1 | Foundation | **done** | Scaffold, FastAPI app, base template, dark mode, Alembic wired, dev scripts, smoke tests 3/3 |
| 2 | Accounts | **done** | Model, CRUD, HTMX forms, page list, dashboard cards, JSON API, 25 test suite |
| 3 | Transactions | **done** | Model, CRUD, HTMX forms, filterable list, transfer flow, 29 tests |
| 4 | Dashboard v1 | **done** | Real charts & KPIs from live data, 16 new tests |
| 5 | Categories & Budgets | **done** | Category CRUD, budget progress bars, 45 new tests |
| 6 | Recurring rules | pending | Auto-materialize on startup |
| 7 | Predictions | pending | EMA + day-of-week seasonality + confidence bands |
| 8 | Polish | pending | Tests, INR seed data, deploy notes, a11y pass |

---

## 3. What was built in Phase 1

### Application code (`backend/app/`)

- `__init__.py` — package marker, exposes `__version__ = "0.1.0"`.
- `main.py` — FastAPI app factory. `lifespan` calls `ensure_data_dir()`. Mounts `/static`, configures `Jinja2Templates` with globals (`app_name`, `default_currency`, `currency_symbol`, `app_env`). Routes: `GET /` (dashboard), `GET /healthz` (liveness).
- `config.py` — `Settings(BaseSettings)` from pydantic-settings. Reads `.env` from project root. Fields: `app_name`, `app_env`, `debug`, `database_url`, `default_currency`, `currency_symbol`, `forecast_history_days`, `forecast_cache_ttl_seconds`, `recurring_auto_materialize`. `@lru_cache get_settings()`.
- `database.py` — SQLAlchemy 2.0 `engine` (with `check_same_thread=False` for SQLite), `SessionLocal`, `Base(DeclarativeBase)`, `get_db()` FastAPI dep, `session_scope()` context manager for scripts, `ensure_data_dir()` helper.
- `deps.py` — re-exports `get_db` for `from app.deps import get_db`.
- `models/`, `schemas/`, `crud/`, `routers/`, `services/` — empty `__init__.py` placeholders, populated per phase.

### Templates (`backend/app/templates/`)

- `base.html` — Tailwind Play CDN with inline config (system font stack, `accent-600` = indigo-600, `positive-600` = emerald-600, `negative-600` = red-600, `darkMode: 'class'`). Loads HTMX 1.9, Alpine 3, Chart.js 4 (deferred). Sticky header with logo + phase-aware nav (Accounts/Transactions active, Budgets/Recurring disabled). Dark-mode toggle button (Alpine + `localStorage` key `ff-dark`). SVG favicon (indigo document icon). Slot `{% block content %}` over a max-w-7xl container. Footer with `/docs` link.
- `dashboard.html` — extends base. Hero with "Dashboard" + Phase 1 status note. 4 KPI cards with real data (Total balance server-rendered; Income/Expense/Savings rate populated client-side from `/api/dashboard/summary`). Per-account cards with computed balances. Real recent-transactions list (last 10). Real Chart.js charts (daily spending bar, category doughnut) initialized via `DOMContentLoaded` listener. 8-phase build-status list (Phases 1-4 green).

### Static (`backend/app/static/`)

- `css/app.css` — small file: `color-scheme: light dark`, smooth theme transition (respects `prefers-reduced-motion`), `-webkit-font-smoothing`, hides the Tailwind Play CDN warning banner.
- `js/app.js` — placeholder; one `console.debug` line. Charts are wired in Phase 4.

### Migrations (`backend/alembic/`)

- `alembic.ini` — standard config; `script_location = alembic`; `sqlalchemy.url` intentionally blank (set programmatically).
- `env.py` — loads `Base.metadata` from `app.database`, sets `sqlalchemy.url` from `get_settings().database_url`, imports `app.models` (currently empty package, will grow), uses `render_as_batch=True` for SQLite ALTER support. Supports `offline` and `online` modes.
- `script.py.mako` — standard Alembic template.
- `versions/` — 2 migrations: `1c807833bf32` (accounts, Phase 2), `50a1b87ac679` (transactions, Phase 3).

### Tests (`backend/tests/`)

- `conftest.py` — `db_session` fixture (in-memory SQLite, fresh per test, `Base.metadata.create_all`), `client` fixture (FastAPI `TestClient` with `get_db` overridden), `settings` fixture.
- `test_smoke.py` — 3 tests: `GET /healthz` returns 200 with correct JSON, `GET /` returns 200 containing "FutureFunds" and "Dashboard", `GET /static/css/app.css` returns 200 with `text/css`. **All 3 pass.**

### Scripts (`scripts/`)

- `dev.ps1` (Windows PowerShell 5.1+) — creates `.venv` if missing, activates it, installs `.[dev]`, runs `alembic upgrade head`, starts uvicorn on `127.0.0.1:8000` with `--reload`. Idempotent.
- `dev.sh` (POSIX) — same flow, bash + `source bin/activate`.
- `build_css.sh` — placeholder for future Tailwind standalone-CLI build. Skips cleanly if `tailwindcss` not on PATH.
- `seed.py` — real seeder (upgraded ahead-of-schedule). Creates 4 accounts (Wallet, HDFC Bank, SBI Savings, Axis Credit Card) + 11 transaction rows with INR amounts. Runs `alembic upgrade head` programmatically.

### Root files

- `README.md` — identity, **build status table**, one-shot dev launcher as primary quick-start, manual setup fallback, endpoints table, expanded project layout, frontend notes, scripts reference.
- `PLAN.md` — full living design doc: tech stack rationale, design tokens, directory layout, database schema, routes, forecasting algorithm, recurring engine, phased roadmap, dev workflow, free-hosting notes, future-proofing, **changelog** (Phase 1 complete with verification; Phase 2 next with concrete sub-plan).
- `STATUS.md` — **this file**.
- `.env.example` — `APP_NAME`, `APP_ENV`, `DEBUG`, `DATABASE_URL`, `DEFAULT_CURRENCY=INR`, `CURRENCY_SYMBOL=₹`, forecast + recurring config.
- `.gitignore` — Python caches, venv, `data/*.db*`, `.env`, editor cruft, logs.
- `pyproject.toml` — dependencies, optional `[dev]`, ruff config, pytest config. **Note: dropped `readme = "../README.md"`** because setuptools refuses paths outside the package directory. Runtime is unaffected; only matters when packaging for PyPI.
- `requirements.txt` — pip-friendly copy of dependencies.

---

## 4. What was verified (latest session — Phase 5)

- ✅ `pytest -q` → **134 passed, 0 failed** (3 smoke + 24 accounts + 21 categories + 24 budgets + 7 config + 16 dashboard + 39 transactions).
- ✅ `GET /api/dashboard/summary` returns income/expense/net/savings_rate.
- ✅ `GET /api/dashboard/spending?range=7` returns 7 daily entries with proper amounts.
- ✅ `GET /api/dashboard/category-breakdown` returns breakdown by type (falls back when no categories assigned).
- ✅ `GET /api/dashboard/category-breakdown` returns category names/colors when categories are assigned to transactions.
- ✅ `GET /api/dashboard/budgets` returns budget progress with spent, percentage, remaining.
- ✅ `GET /api/accounts/1/balance-history?range=7` returns daily running balance.
- ✅ `GET /` renders canvas elements (`id="spending-chart"`, `id="category-chart"`), KPI placeholder IDs (`id="kpi-income"`, etc.), and budget progress container (`id="budget-section"`, `id="budget-progress-container"`).
- ✅ `GET /docs` serves auto-generated OpenAPI docs including dashboard and category/budget endpoints.
- ✅ Full CRUD round-trip for categories via HTMX (create → edit → delete).
- ✅ Full CRUD round-trip for budgets via HTMX (create → edit → delete) with live progress bars.
- ✅ `ruff check .` — all clean.

---

## 5. Decisions already made — don't relitigate

1. **No build step for the frontend in v1.** Tailwind via Play CDN; HTMX/Alpine/Chart.js from CDN with `defer`. Production compiled CSS is a Phase 8 task (`scripts/build_css.sh` is the hook).
2. **Single currency, configurable.** No FX conversion. `currency_symbol` can be overridden in `.env`.
3. **Sync SQLAlchemy.** Async is unnecessary for this workload and complicates the schema-explorer story.
4. **HTMX form-submit endpoints return `HX-Redirect`, not partials.** JSON API endpoints (`/api/...`) are reserved for Chart.js data. Create/edit forms live on dedicated full-page views (e.g. `/accounts/new`) where target elements like `#account-list` don't exist, so HTMX silently discards partial responses. POST/PATCH now return `Response(headers={"HX-Redirect": "/accounts"})` instead. DELETE endpoints still return 200 with `HX-Trigger` — the list page re-fetches via HTMX.
5. **Transfers** = two `transactions` rows (one negative, one positive) sharing `transfer_pair_id`. No separate `transfers` table.
6. **Local-first.** No auth in v1. `deps.get_current_user` is a planned no-op slot; the schema and codebase leave room for a `users` table + `user_id` FK on every model without major refactors.
7. **Recurring rules** are materialized into real `transactions` rows (not virtual). `last_generated_date` is the idempotency key. Auto-materialize runs on FastAPI startup if `RECURRING_AUTO_MATERIALIZE=true`.

---

## 6. Conventions to follow

- **Package layout**: `models/` (ORM), `schemas/` (Pydantic DTOs), `crud/` (pure DB functions), `routers/` (FastAPI APIRouter), `services/` (business logic), `templates/` (Jinja2), `static/` (assets). One module per concept.
- **Naming**: snake_case for files, functions, variables. PascalCase for classes/models. Pydantic schemas: `XxxCreate`, `XxxUpdate`, `XxxRead`. HTMX partials: `partials/<thing>_<action>.html`.
- **Currency formatting in templates**: always use `{{ currency_symbol }}{{ amount|format_inr }}` once a Jinja filter is added; for now, hard-code `₹` is fine.
- **Design tokens** (from `PLAN.md` §3): `accent-600` (indigo, single accent), `positive-600` (emerald, income/in-budget), `negative-600` (red, expense/over-budget), `rounded-lg`, system font, no shadows. Dark mode is automatic via `dark:` variants.
- **Tests**: every new model and router should have at least one test in `backend/tests/`. Use the existing `client` and `db_session` fixtures.
- **Alembic**: always run `alembic revision --autogenerate -m "<short description>"` from `backend/`. The `env.py` already wires up `Base.metadata` and `render_as_batch=True`.

---

## 7. Quick command reference

```bash
# Activate venv (after first dev.ps1 / dev.sh run)
# Windows:
backend\.venv\Scripts\activate
# POSIX:
source backend/.venv/bin/activate

# Run the dev server (auto-reload)
# Windows:
.\scripts\dev.ps1
# POSIX:
./scripts/dev.sh

# Run tests
cd backend && pytest

# Seed demo data (from project root)
python scripts/seed.py

# Create a new migration
cd backend && alembic revision --autogenerate -m "add accounts table"

# Apply migrations
cd backend && alembic upgrade head

# Lint
cd backend && ruff check .
```

---

## 8. Next up: Phase 6 — Recurring rules

Phase 6 adds the `RecurringRule` model + migration, `services/recurring.py` materializer, auto-run on startup, and a "next 5 occurrences" preview. See `PLAN.md` §14 for the concrete checklist.

## 9. Completed phases

### Phase 5 — Categories & Budgets

Shipped:
- `app/models/category.py` — `Category` ORM model with `CategoryType` enum (expense/income), nullable self-FK `parent_id`, color, icon.
- `app/models/budget.py` — `Budget` ORM model with `BudgetPeriod` enum (weekly/monthly/yearly), FK to `categories.id`, decimal `amount`, `start_date`, `is_active`, `TimestampMixin`.
- `app/models/transaction.py` — `category_id` changed from plain `Integer` to `ForeignKey("categories.id")` with `category` relationship.
- `app/models/__init__.py` — imports `Budget`, `BudgetPeriod`, `Category`, `CategoryType`.
- Alembic migration `2a9b3c7def01` — creates `categories` and `budgets` tables; adds FK on `transactions.category_id`.
- `app/schemas/category.py`, `app/schemas/budget.py` — Pydantic DTOs (Create/Update/Read).
- `app/schemas/transaction.py` — `TransactionCreate`/`TransactionUpdate` now include optional `category_id`.
- `app/crud/category.py` — CRUD with type filter, default color, deletion guard for transactions.
- `app/crud/budget.py` — CRUD with active-only filter.
- `app/crud/transaction.py` — `create_transaction` accepts optional `category_id`.
- `app/routers/categories.py` — 3 HTML pages, 3 HTMX mutations, 2 JSON API endpoints.
- `app/routers/budgets.py` — 3 HTML pages, 3 HTMX mutations, 2 JSON API endpoints. List page renders live progress bars.
- `app/services/analytics.py` — `category_breakdown` updated to group by real `Category` (falls back to type-based); `budget_progress` added (per-budget spend/percentage/remaining/over-budget).
- `app/routers/dashboard.py` — new `GET /api/dashboard/budgets` endpoint.
- Templates: `categories/list.html`, `categories/form.html`, `budgets/list.html`, `budgets/form.html`, `partials/category_card.html`, `partials/budget_card.html`.
- `app/templates/base.html` — "Categories" nav added; "Budgets" nav enabled; footer "Phase 5".
- `app/templates/dashboard.html` — budget progress section rendered client-side; category doughnut uses per-item colors; Phase 5 build status green.
- `app/main.py` — mounts `categories_router` and `budgets_router`.
- `tests/test_categories.py` — 21 tests (CRUD + HTML + HTMX + JSON + validation). All pass.
- `tests/test_budgets.py` — 24 tests (CRUD + budget_progress scenarios + HTML + HTMX + JSON + validation + dashboard endpoint). All pass.

Key decisions during implementation:
- `category_breakdown` groups by real categories when transactions have them assigned; falls back to type-based grouping for backward compatibility.
- Budget progress is computed on-the-fly from transactions (not stored) — sums expenses per category within the current period.
- Dashboard budget progress is fetched client-side from `/api/dashboard/budgets` and rendered with inline HTML progress bars.
- The category form is deliberately simple (no `parent_id` UI) — self-referencing categories can be added in a future pass.

Verified:
- `pytest -q` → **134 passed** (3 smoke + 24 accounts + 21 categories + 24 budgets + 7 config + 16 dashboard + 39 transactions).
- `GET /categories` renders list with empty state and "Add category" CTA.
- `GET /budgets` renders list with progress bars from live transactions.
- `GET /api/dashboard/budgets` returns budget progress JSON.
- `GET /api/dashboard/category-breakdown` returns category names/colors when assigned.
- Full CRUD round-trip for categories and budgets via HTMX.
- `ruff check .` — all clean.

### Phase 4 — Dashboard v1

Shipped:
- `app/services/analytics.py` — analytics service with `monthly_summary`, `daily_spending`, `category_breakdown`, and `balance_history` functions. All return structured data for the dashboard JSON API.
- `app/routers/dashboard.py` — 4 JSON API endpoints:
  - `GET /api/dashboard/summary?year=&month=` — monthly income, expense, net, savings rate
  - `GET /api/dashboard/spending?range=30` — daily expense bar chart data
  - `GET /api/dashboard/category-breakdown?month=YYYY-MM` — breakdown by type (placeholder until categories exist in Phase 5)
  - `GET /api/accounts/{id}/balance-history?range=90` — daily running balance per account
- `app/main.py` — dashboard router mounted
- `app/templates/dashboard.html` — real KPIs (income, expense, savings rate) loaded via JS from `/api/dashboard/summary`; daily spending bar chart (Chart.js) from `/api/dashboard/spending`; category breakdown doughnut chart (Chart.js) from `/api/dashboard/category-breakdown`; Phase 4 build status now green.
- `app/templates/base.html` — added `{% block scripts %}{% endblock %}` slot; footer updated to "Phase 4".
- `tests/test_dashboard.py` — 16 tests covering all analytics functions and HTTP endpoints.

Key decisions during implementation:
- Chart.js is loaded with `defer` in `base.html`; dashboard charts are initialized in a `DOMContentLoaded` listener so all deferred scripts (Alpine, Chart.js) are guaranteed available.
- KPIs are updated client-side via `fetch()` to the JSON API, keeping the server-rendered dashboard static and fast.
- `category_breakdown` groups by transaction type (income/expense/transfer) as a fallback until the `categories` table exists in Phase 5.
- All monetary amounts are returned as strings from the API (to preserve Decimal precision) and parsed client-side for chart rendering.

Verified:
- `pytest -q` → **89 passed** (3 smoke + 24 accounts + 7 config + 39 transactions + 16 dashboard).
- `GET /api/dashboard/summary` returns correct monthly totals.
- `GET /api/dashboard/spending?range=7` returns 7 daily entries with proper amounts.
- `GET /api/dashboard/category-breakdown` returns breakdown by type.
- `GET /api/accounts/1/balance-history?range=7` returns daily running balance.
- Dashboard page renders with `id="spending-chart"`, `id="category-chart"`, `id="kpi-income"`, etc.
- KPI cards show real data populated by client-side fetch.

### Phase 2 — Accounts

Shipped:
- `app/models/account.py` — `Account` ORM model with `AccountType` enum (cash, bank, credit_card, savings, investment), `Numeric(18,2) opening_balance`, `TimestampMixin` (created_at/updated_at), default color per type via `ACCOUNT_TYPE_COLORS` dict.
- `app/models/__init__.py` — added `TimestampMixin` + imports `Account`.
- Alembic migration `1c807833bf32` — creates `accounts` table with `id, name, type (Enum), currency, opening_balance, color, icon, is_active, created_at, updated_at`. Applied.
- `app/schemas/account.py` — `AccountCreate`, `AccountUpdate` (all optional for patch), `AccountRead` (with `from_attributes=True`).
- `app/crud/account.py` — `list_accounts`, `get_account`, `create_account`, `update_account`, `delete_account`, `compute_balance` (returns `opening_balance` until Phase 3).
- `app/templates.py` — new shared module; Jinja2Templates instance extracted from `main.py` for reuse across routers (avoids circular imports).
- `app/main.py` — refactored: removed inline template setup, moved dashboard route to `routers/pages.py`, routers imported inline to avoid circular deps.
- `app/routers/pages.py` — `GET /` dashboard with real total balance, per-account cards, empty-state CTA, build-status panel (Phase 2 now green).
- `app/routers/accounts.py` — full CRUD router: 3 HTML pages (`/accounts`, `/accounts/new`, `/accounts/{id}/edit`), 3 HTMX mutation endpoints (`POST`, `PATCH`, `DELETE`) with JSON fallback, 3 JSON API endpoints (`GET /api/accounts`, `GET /api/accounts/{id}`, `GET /api/accounts/{id}/balance`), `Optional[Form(None)]` for PATCH fields, `_respond_with_card` helper.
- `app/templates/accounts/list.html` — grid layout, empty state, "Add account" CTA, per-card edit/delete buttons (HTMX, with confirmation dialog).
- `app/templates/accounts/form.html` — single template for create/edit (`mode`, `account` context), HTMX form with `hx-post`/`hx-patch`, `hx-target`, `hx-swap`, reset-on-success, color preview swatch, type dropdown with per-option color data attributes.
- `app/templates/partials/account_card.html` — first-letter initial icon, color stripe, type badge, balance, hover-visible edit/delete actions (HTMX `hx-delete` with `hx-confirm`). Reused by list page, dashboard, and HTMX responses.
- `app/templates/dashboard.html` — real total balance KPI card with account count, per-account cards with initial+color+balance, empty-state CTA for new accounts. Phase 2 status indicator updated to green.
- `app/templates/base.html` — nav "Accounts" link now active (points to `/accounts`). Phase 3/5/6 items remain disabled.
- `tests/test_accounts.py` — 20 tests: enum values, default color, CRUD operations, non-existent entity handling, balance computation, 3 HTML page tests, 3 HTMX mutation tests, 3 JSON API tests, 2 validation failure tests. All pass.
- `tests/conftest.py` — refactored to use temporary file-based SQLite (avoids in-memory per-connection issue with TestClient threading). `tmp_db_path` + separate `client` engine.
- `pyproject.toml` — added `python-multipart` dependency (required by `Form()`).

Key decisions during implementation:
- Used `Optional[Form(None)]` for PATCH params and built a filtered dict (not a flat schema) to avoid writing `None` into NOT NULL columns.
- TestClient with in-memory SQLite fails because the background thread creates a new connection to a different in-memory database. Fixed by switching tests to a temporary file-based SQLite.
- HTMX forms use `application/x-www-form-urlencoded` (not JSON) — `Form()` was required, not `Body()`.
- `AccountUpdate` expects only the fields that the client actually sends; `exclude_unset=True` is used in `update_account` (achieved by building patch dict manually).

Verified:
- `pytest -q` → **25 passed** (3 smoke + 20 accounts + 2 additional helpers).
- `GET /` renders dashboard with placeholder for empty DB state + build status.
- `GET /accounts` renders empty list with "Add your first account" CTA.
- `GET /accounts/new` renders form with type dropdown, colour picker, currency defaulting to INR.
- `GET /healthz` returns `{"status":"ok","app":"FutureFunds"}`.
- Full CRUD round-trip: create → see card → edit name → card updates → delete → card removed (via HTMX).

### Phase 3 — Transactions

Shipped:
- `app/models/transaction.py` — `Transaction` ORM model with `TransactionType` enum (expense/income/transfer), signed `amount`, FKs to `accounts.id` and self-FK `transfer_pair_id`, nullable `category_id`/`recurring_rule_id` (FK constraints deferred to Phases 5 & 6).
- Alembic migration `50a1b87ac679` — creates `transactions` table with indexes on `(date)` and `(account_id, date)`. Applied.
- `app/schemas/transaction.py` — `TransactionCreate`, `TransactionUpdate`, `TransactionRead`, `TransferCreate` Pydantic DTOs.
- `app/crud/transaction.py` — `list_transactions` (filterable by account/type/date range/description), `get_transaction`, `create_transaction`, `update_transaction`, `delete_transaction`, `create_transfer` (two rows sharing `transfer_pair_id`), `compute_account_balance`, `get_recent_transactions`.
- `app/crud/account.py` — `compute_balance` updated to sum opening + transactions (real balance).
- `app/routers/transactions.py` — 3 HTML pages, 3 HTMX mutation endpoints, 2 JSON API endpoints. Transfer flow via `from_account_id`/`to_account_id` fields. Amount validation in router layer.
- Templates: `transactions/list.html` (filterable), `transactions/form.html` (create/edit with JS transfer toggle), `partials/transaction_row.html`, `partials/transaction_list_items.html` (HTMX partial swaps).
- Dashboard: real recent-transactions list (last 10), computed balances in account cards, Phase 3 status green.
- `app/main.py` — mounts `transactions_router`.
- `app/templates/base.html` — "Transactions" nav active. Footer "Phase 3".
- `tests/test_transactions.py` — 29 tests: model, CRUD, filters, transfers, balance, HTML pages, HTMX mutations, JSON API, validation. All pass.

Key decisions during implementation:
- `amount` is stored signed; form input is always positive, sign applied per `type`.
- Transfers are a single form POST creating two rows sharing `transfer_pair_id`.
- `category_id`/`recurring_rule_id` are plain nullable `Integer` columns (no FK) until their tables exist.
- Amount `> 0` validation in the router layer (form data bypasses Pydantic schema validation).

Verified:
- `pytest -q` → **54 passed** (3 smoke + 20 accounts + 2 helpers + 29 transactions).
- `GET /transactions` renders filter form + empty state.
- `GET /transactions/new` renders form with account dropdown + transfer toggle.
- Full CRUD round-trip via HTMX (create → edit → delete).
- Transfer from A to B updates both balances correctly.

#### Post-Phase 3 bugfixes

These fixes were applied in a follow-up session and are stable in the codebase:

- **Datepicker calendar icon invisible in dark mode** (`BUG`): The native calendar icon on
  `<input type="date">` renders black-on-dark in Chromium browsers when toggled to dark mode.
  `color-scheme: dark` and `::-webkit-calendar-picker-indicator { filter: invert(1) }`
  were applied but did not resolve the issue (likely a Tailwind Play CDN cascade or browser
  shadow-DOM limitation). **Marked as deferred — needs investigation in Phase 8 or when
  Tailwind Play CDN is replaced with compiled CSS.**

- **HTMX form redirect**: POST/PATCH on accounts and transactions returned partial HTML
  targeted at `#account-list` / `#transaction-list`, but those elements don't exist on
  dedicated form pages. Changed to `HX-Redirect`. Removed dead `hx-target`/`hx-swap`
  from form templates. Tests updated to use JSON API for entity ID lookup.
- **DELETE route restoration**: `@router.delete("/transactions/{id}")` was accidentally
  deleted during the HTMX refactor. Restored.
- **Filter 422 fix**: `account_id` param changed from `int | None` to `str | None`
  with manual parsing to accept empty string submissions from the HTML filter form.
- **Checkbox save fix**: Added hidden `<input type="hidden" name="is_active" value="false" />`
  after the `is_active` checkbox so that unchecking sends `false` to the server.
- **Seed script**: Upgraded from placeholder to real seeder (4 accounts, 11 txns, INR amounts,
  Alembic-driven). Run via `python scripts/seed.py` from project root.

---

## 10. Where to look first if confused

| Question | File |
|---|---|
| "What's the overall design?" | `PLAN.md` |
| "How do I run it?" | `README.md` |
| "Where are we right now?" | `STATUS.md` (this file) |
| "What does the design look like?" | `PLAN.md` §3 (visual tokens), §4 (layout), §5 (schema) |
| "What endpoint handles X?" | `PLAN.md` §6 (routes) |
| "How does forecasting work?" | `PLAN.md` §7 |
| "What changed last?" | `PLAN.md` §14 (changelog) |
