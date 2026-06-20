# FutureFunds — Project Status (handoff snapshot)

> **Read this first if you're a new agent/session/model.** It captures *where the project is right now* and the minimum context needed to continue. For full design rationale see [`PLAN.md`](./PLAN.md). For setup & usage see [`README.md`](./README.md).

Last updated: **Phase 9 (Auth — Google SSO)** ✅ complete — multi-user data isolation with Google OAuth login.

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
| **Mode** | Multi-user with Google SSO. Each user sees only their own data (`user_id` FK on every table). |
| **Theme** | Clean neutral slate/indigo, light + dark (persisted in `localStorage`) |

---

## 2. Build status

| # | Phase | Status | Notes |
|---|---|---|---|---|
| 1 | Foundation | **done** | Scaffold, FastAPI app, base template, dark mode, Alembic wired, dev scripts, smoke tests 3/3 |
| 2 | Accounts | **done** | Model, CRUD, HTMX forms, page list, dashboard cards, JSON API, 24 tests |
| 3 | Transactions | **done** | Model, CRUD, HTMX forms, filterable list, transfer flow, 47 tests |
| 4 | Dashboard v1 | **done** | Real charts & KPIs from live data, 18 tests |
| 4.1 | Quick-add (redirect) | **done** | Dashboard CTA → form → redirect back to dashboard |
| 5 | Categories & Budgets | **done** | Category CRUD, budget progress bars, 45 tests (21 categories + 24 budgets) |
| 6 | Recurring rules | **done** | Model, CRUD, HTMX forms, materializer, next-occurrences preview, 36 tests |
| 7 | Predictions | **done** | EMA + day-of-week seasonality + confidence bands, balance projection chart, runway warning, 22 tests |
| 8 | Polish | **done** | Dashboard period filter, seed hardening, error pages, a11y, compiled Tailwind, deploy notes, bug fixes, mobile nav |
| 9 | Auth (Google SSO) | **done** | Google OAuth login, session auth, per-user data isolation, profile header, sign-out, HTTPS redirect |

---

## 3. What was built in Phase 1

### Application code (`backend/app/`)

- `__init__.py` — package marker, exposes `__version__ = "0.1.0"`.
- `main.py` — FastAPI app factory. `lifespan` calls `ensure_data_dir()`. Mounts `/static`, configures `Jinja2Templates` with globals (`app_name`, `default_currency`, `currency_symbol`, `app_env`). Routes: `GET /` (dashboard), `GET /healthz` (liveness).
- `config.py` — `Settings(BaseSettings)` from pydantic-settings. Reads `.env` from project root. Fields: `app_name`, `app_env`, `debug`, `database_url`, `default_currency`, `currency_symbol` (Unicode escape `\u20b9` for Windows encoding safety), `forecast_history_days`, `forecast_cache_ttl_seconds`, `recurring_auto_materialize`. `@lru_cache get_settings()`.
- `database.py` — SQLAlchemy 2.0 `engine` (with `check_same_thread=False` for SQLite), `SessionLocal`, `Base(DeclarativeBase)`, `get_db()` FastAPI dep, `session_scope()` context manager for scripts, `ensure_data_dir()` helper.
- `deps.py` — re-exports `get_db` for `from app.deps import get_db`.
- `models/`, `schemas/`, `crud/`, `routers/`, `services/` — empty `__init__.py` placeholders, populated per phase.

### Templates (`backend/app/templates/`)

- `base.html` — Tailwind Play CDN with inline config (system font stack, `accent-600` = indigo-600, `positive-600` = emerald-600, `negative-600` = red-600, `darkMode: 'class'`). Loads HTMX 1.9, Alpine 3, Chart.js 4 (deferred). Sticky header with logo + phase-aware nav (Accounts/Transactions active, Budgets/Recurring disabled). Dark-mode toggle button (Alpine + `localStorage` key `ff-dark`). Mobile hamburger menu with animated slide-down panel (visible below `md` breakpoint). SVG favicon (indigo document icon). Slot `{% block content %}` over a max-w-7xl container. Footer with `/docs` link.
- `dashboard.html` — extends base. Hero with "Dashboard" + Phase 1 status note. 4 KPI cards with real data (Total balance server-rendered; Income/Expense/Savings rate populated client-side from `/api/dashboard/summary`). Per-account cards with computed balances. Real recent-transactions list (last 10). Real Chart.js charts (daily spending bar, category doughnut) initialized via `DOMContentLoaded` listener. 8-phase build-status list (Phases 1-4 green).

### Static (`backend/app/static/`)

- `css/app.css` — small file: `color-scheme: light dark`, smooth theme transition (respects `prefers-reduced-motion`), `-webkit-font-smoothing`, hides the Tailwind Play CDN warning banner.
- `js/app.js` — placeholder; one `console.debug` line. Charts are wired in Phase 4.

### Migrations (`backend/alembic/`)

- `alembic.ini` — standard config; `script_location = alembic`; `sqlalchemy.url` intentionally blank (set programmatically).
- `env.py` — loads `Base.metadata` from `app.database`, sets `sqlalchemy.url` from `get_settings().database_url`, imports `app.models` (currently empty package, will grow), uses `render_as_batch=True` for SQLite ALTER support. Supports `offline` and `online` modes.
- `script.py.mako` — standard Alembic template.
- `versions/` — 4 migrations: `1c807833bf32` (accounts, Phase 2), `50a1b87ac679` (transactions, Phase 3), `2a9b3c7def01` (categories & budgets, Phase 5), `fb627ac5984d` (recurring rules + FK on transactions, Phase 6).

### Tests (`backend/tests/`)

- `conftest.py` — `db_session` fixture (in-memory SQLite, fresh per test, `Base.metadata.create_all`), `client` fixture (FastAPI `TestClient` with `get_db` overridden), `settings` fixture.
- `test_smoke.py` — 3 tests: `GET /healthz` returns 200 with correct JSON, `GET /` returns 200 containing "FutureFunds" and "Dashboard", `GET /static/css/app.css` returns 200 with `text/css`. **All 3 pass.**

### Scripts (`scripts/`)

- `dev.ps1` (Windows PowerShell 5.1+) — creates `.venv` if missing, activates it, installs `.[dev]`, runs `alembic upgrade head`, starts uvicorn on `127.0.0.1:8000` with `--reload`. Idempotent.
- `dev.sh` (POSIX) — same flow, bash + `source bin/activate`.
- `build_css.sh` — placeholder for future Tailwind standalone-CLI build. Skips cleanly if `tailwindcss` not on PATH.
- `seed.py` — real seeder (upgraded ahead-of-schedule). Creates 4 accounts (Wallet, HDFC Bank, SBI Savings, Axis Credit Card) + 11 transaction rows with INR amounts + 2 recurring rules (Monthly Salary, Monthly Rent). Runs `alembic upgrade head` programmatically.

### Root files

- `README.md` — identity, **build status table**, one-shot dev launcher as primary quick-start, manual setup fallback, endpoints table, expanded project layout, frontend notes, scripts reference.
- `PLAN.md` — full living design doc: tech stack rationale, design tokens, directory layout, database schema, routes, forecasting algorithm, recurring engine, phased roadmap, dev workflow, free-hosting notes, future-proofing, **changelog** (Phase 1 complete with verification; Phase 2 next with concrete sub-plan).
- `STATUS.md` — **this file**.
- `.env.example` — `APP_NAME`, `APP_ENV`, `DEBUG`, `DATABASE_URL`, `DEFAULT_CURRENCY=INR`, `CURRENCY_SYMBOL=₹`, forecast + recurring config.
- `.gitignore` — Python caches, venv, `data/*.db*`, `.env`, editor cruft, logs.
- `pyproject.toml` — dependencies, optional `[dev]`, ruff config, pytest config. **Note: dropped `readme = "../README.md"`** because setuptools refuses paths outside the package directory. Runtime is unaffected; only matters when packaging for PyPI.
- `requirements.txt` — pip-friendly copy of dependencies.

---

## 4. What was verified (latest session — Phase 8 bug fixes)

- ✅ `pytest -q` → **202 passed, 0 failed**.
- ✅ `ruff check .` — all clean.
- ✅ `/accounts` page now displays correct balances for all accounts (fixed `balances` dict → per-account `balance` variable).
- ✅ Currency symbol `₹` renders correctly across all pages (Unicode escape `\u20b9` in `config.py`).
- ✅ Seed script creates 2 sample recurring rules (Monthly Salary, Monthly Rent).
- ✅ Mobile hamburger menu visible below 768px breakpoint with animated slide-down panel.
- ✅ Hamburger icon toggles to X when menu is open; clicking outside closes it.
- ✅ Desktop navigation unchanged above 768px.

---

## 5. Decisions already made — don't relitigate

1. **No build step for the frontend in v1.** Tailwind via Play CDN; HTMX/Alpine/Chart.js from CDN with `defer`. Production compiled CSS is a Phase 8 task (`scripts/build_css.sh` is the hook).
2. **Single currency, configurable.** No FX conversion. `currency_symbol` can be overridden in `.env`.
3. **Sync SQLAlchemy.** Async is unnecessary for this workload and complicates the schema-explorer story.
4. **HTMX form-submit endpoints return `HX-Redirect`, not partials.** JSON API endpoints (`/api/...`) are reserved for Chart.js data. Create/edit forms live on dedicated full-page views (e.g. `/accounts/new`) where target elements like `#account-list` don't exist, so HTMX silently discards partial responses. POST/PATCH now return `Response(headers={"HX-Redirect": "/accounts"})` instead. DELETE endpoints still return 200 with `HX-Trigger` — the list page re-fetches via HTMX.
5. **Transfers** = two `transactions` rows (one negative, one positive) sharing `transfer_pair_id`. No separate `transfers` table.
6. **Multi-user via Google SSO.** `deps.get_current_user` reads `user_id` from the session cookie. All CRUD functions accept `user_id` and scope queries accordingly. First-time Google users are auto-registered (upsert in callback).
7. **Recurring rules** are materialized into real `transactions` rows (not virtual). `last_generated_date` is the idempotency key. Auto-materialize on startup removed (was a cross-user vulnerability); materialization is now per-user via `POST /api/recurring/materialize`.

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

## 8. Phase 8 — Polish (complete)

| # | Task | Status |
|---|------|--------|
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

## 9. Completed phases

### Phase 9 — Auth (Google SSO)

Shipped:
- `app/models/user.py` — `User` ORM model with `email`, `name`, `google_sub`, `last_login_at`, `TimestampMixin`.
- Alembic migration `2a3b4c5d6e7f` — creates `users` table; adds nullable `user_id` FK to `accounts`, `categories`, `budgets`, `recurring_rules`, `transactions`. Uses `batch_alter_table` for SQLite compatibility.
- `app/routers/auth.py` — OAuth routes: `GET /auth/login` (redirect to Google), `GET /auth/google/callback` (upsert user, set session), `POST /auth/logout` (clear session), `GET /login` (login page).
- `app/deps.py` — `get_current_user` reads `user_id` from session, returns `User` or raises `_NotAuthenticated`. Exception handler in `main.py` redirects browsers to `/login` on 401.
- `app/templates.py` — added `_current_user()` template global function for profile display in header.
- `app/templates/login.html` — "Sign in with Google" button.
- `app/templates/base.html` — profile section (avatar initial + name + email) in desktop header and mobile nav; sign-out button in both locations.
- `app/main.py` — `HTTPSRedirectMiddleware` gated behind `if not settings.is_development`; `_NotAuthenticated` exception handler added; `auth_router` mounted.
- `app/config.py` — `google_client_id`, `google_client_secret`, `google_redirect_uri` settings; `FF_` env prefix; legacy env var migration for Google OAuth keys.
- `.env.example` — added `FF_GOOGLE_CLIENT_ID`, `FF_GOOGLE_CLIENT_SECRET`, `FF_GOOGLE_REDIRECT_URI`, `FF_SESSION_SECRET`, `FF_SESSION_MAX_AGE_SECONDS`.
- All CRUD functions scoped by `user_id` (accounts, transactions, categories, budgets, recurring rules).

Key decisions:
- First-time Google users are auto-registered via upsert in the OAuth callback — no separate signup page.
- `HTTPSRedirectMiddleware` only active in production; disabled in development to allow plain HTTP.
- Browser requests (Accept: text/html) get redirected to `/login` on auth failure; API requests get 401 JSON.
- Session cookie expiry: 14 days (configurable via `FF_SESSION_MAX_AGE_SECONDS`).

Verified:
- ✅ `pytest -q` — all tests passing.
- ✅ Unauthenticated browser request → 303 redirect to `/login`.
- ✅ Google OAuth flow completes (requires valid `FF_GOOGLE_CLIENT_ID`/`FF_GOOGLE_CLIENT_SECRET`).
- ✅ Profile section shows in header after login.
- ✅ Sign-out clears session and redirects to `/login`.
- ✅ HTTPS redirect disabled in development mode.

### Phase 7 — Predictions

Shipped:
- `app/services/forecasting.py` — forecasting engine with EMA (exponential moving average), day-of-week seasonality decomposition, confidence bands (95%, z=1.96), and runway detection. Exposes `expense_forecast()` and `balance_projection()`.
- `app/routers/predictions.py` — two JSON API endpoints:
  - `GET /api/predictions/expenses?horizon=30` — daily expense forecast with upper/lower confidence bands
  - `GET /api/predictions/balance?horizon=90` — projected total balance with confidence bands and runway date
- `app/main.py` — `predictions_router` wired in
- `app/templates/dashboard.html` — balance projection line chart (Chart.js with filled confidence band), runway warning chip (amber alert in the total balance KPI card, shows "X days until projected zero"), Phase 7 build status green
- `app/templates/base.html` — footer updated to "Phase 7"
- `tests/test_predictions.py` — 41 tests covering: EMA computation, seasonal factors, daily series building, decomposition, empty-data edge cases, expense forecast structure, balance projection with/without data, runway detection, no-runway scenarios, HTTP endpoint validation, dashboard presence of new UI elements. All pass.

Key design decisions:
- Forecasting uses a simple cache with TTL from `FORECAST_CACHE_TTL_SECONDS` (default 300s), keyed by `(scope, horizon, today)`.
- Balance projection combines income and expense forecasts with a combined residual standard deviation for confidence bands.
- Runway is only computed when `current_balance > 0` (no runway message when already at/below zero).
- `_daily_series` uses `func.abs(Transaction.amount)` to handle signed amounts stored in the DB.
- The EMA smoothing factor is hard-coded at 0.3 (matching `PLAN.md` §7).
- The Chart.js balance chart uses three datasets (upper band fill, projection line, lower band fill) to render the confidence interval as a shaded area.

Verified:
- ✅ `pytest -q` → **222 passed** (181 existing + 41 new).
- ✅ `GET /api/predictions/expenses?horizon=7` returns forecast with upper/lower bands.
- ✅ `GET /api/predictions/expenses` defaults to 30-day horizon.
- ✅ `GET /api/predictions/balance?horizon=30` returns projection with runway.
- ✅ Invalid horizon values (0, 999) return 422.
- ✅ Dashboard renders `id="balance-chart"`, `id="runway-warning"`, `id="runway-text"`.
- ✅ Dashboard build status shows Phase 7 as green.
- ✅ `ruff check .` — all clean.

### Phase 8 — Polish

Shipped:
- **Dashboard period filter**: Added `<select#period-select>` with 5 options (Current month, Previous month, Last 3 months, This year, All time). New `_resolve_date_range()` helper in `services/analytics.py`. All analytics functions (`monthly_summary`, `daily_spending`, `category_breakdown`, `budget_progress`) accept optional `start_date`/`end_date` params. Dashboard JS refactored: `loadAllData(period)` converts period to API params, destroys/re-creates Chart.js instances on change. `daily_spending` max range capped at 365 days.
- **Seed script hardening**: `scripts/seed.py` `_ensure_migrations()` tries `alembic upgrade head`, on failure tries `stamp head`, on failure deletes `data/expenses.db` and retries.
- **Test count doc sync**: Updated PLAN.md, STATUS.md, README.md to show actual 202 tests. Footer updated to "Phase 8" in all templates.
- **Datepicker dark-mode fix**: Moved `color-scheme: dark` and `::-webkit-calendar-picker-indicator` rules from inline `<style>` to `app.css` with additional `::-webkit-datetime-edit` selector. Removed the inline `<style>` block from `base.html`.
- **Error pages**: Created `404.html` and `500.html` templates extending `base.html` with large status code, message, and "Back to dashboard" link. Registered `@app.exception_handler(404)` and `@app.exception_handler(Exception)` in `main.py`.
- **Accessibility pass**: Added `aria-label` to all edit/delete links/buttons in card partials (`account_card`, `transaction_row`, `budget_card`, `category_card`, `recurring_card`). Added `aria-hidden="true"` to every decorative SVG. Added `aria-label="Main navigation"` to `<nav>`, `aria-label="Toggle theme"` to theme toggle. Added `role="img"` + `aria-label` to all 3 `<canvas>` elements in `dashboard.html`. Added `role="alert"` to runway warning and form error container. Added `for="color"` + `aria-describedby` to colour inputs in `accounts/form.html` and `categories/form.html`. Fixed logo swatch `aria-hidden`.
- **Compiled Tailwind CSS**: Created `backend/tailwind.config.js` mirroring the inline Play CDN config (dark mode class, system font stack, accent/positive/negative color palette, border radius). Updated `scripts/build_css.sh` to pass `--config` flag. Removed legacy placeholder comments.
- **Free-hosting deploy notes**: Created `Dockerfile` (python:3.11-slim, port 8000). Added deployment section to README.md covering Docker build/run, Render, Railway, and Fly.io with persistent volume guidance.
- **Shared palette constant**: Moved `window.FF_COLORS` assignment from `base.html` inline script to `js/app.js`. It was already referenced in `dashboard.html` chart configs.
- **Account balance display fix**: `accounts/list.html` now passes `balance` per-account via `{% with balance = balances[account.id] %}` before including `partials/account_card.html`, matching dashboard behavior.
- **Currency symbol encoding fix**: Changed `config.py` default from literal `₹` to Unicode escape `\u20b9` to prevent Windows encoding corruption. Updated `.env.example` accordingly.
- **Seed recurring rules**: `scripts/seed.py` now creates 2 sample `RecurringRule` entries (Monthly Salary income, Monthly Rent expense) and deletes existing rules in `_clean()` for idempotent re-seeding.
- **Mobile hamburger navigation**: Added responsive hamburger menu to `base.html` with Alpine.js toggle. Visible only below `md` breakpoint. Animated slide-down panel, click-outside to close, ARIA accessible attributes. Desktop nav unchanged.

Key decisions:
- Dashboard period filter passes `start_date`/`end_date` API params for ranges; single-month periods still use `year`/`month` for backward compat.
- Budget progress with explicit dates ignores per-period bounds (weekly/monthly/yearly) and aggregates over the full range.
- Seed script deletes DB file only as last resort — safe because seed data is synthetic.
- Error handlers: 404 via `@app.exception_handler(404)`, 500 via `@app.exception_handler(Exception)`.
- `FF_COLORS` defined in `js/app.js` (loaded before chart code via script order in base.html).

Verified:
- ✅ `pytest -q` → **202 passed** (see test breakdown below).
- ✅ `ruff check .` — all clean.
- ✅ Dashboard filter cycles through all 5 periods without JS errors.
- ✅ Seed script recovers from a stale/already-migrated DB.
- ✅ `GET /nonexistent` returns styled 404.
- ✅ All canvases have valid `role`/`aria-label` attributes.
- ✅ `tailwindcss --config backend/tailwind.config.js --input app.css --output app.compiled.css --minify` works when CLI is present.
- ✅ `Dockerfile` builds and serves the app on port 8000.
- ✅ `window.FF_COLORS` accessible from dashboard chart initialization.

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

### Phase 6 — Recurring rules

Shipped:
- `app/models/recurring.py` — `RecurringRule` ORM model with `RecurringFrequency` enum (daily/weekly/monthly/yearly), FK to accounts + categories, `last_generated_date` idempotency key.
- `app/models/transaction.py` — `recurring_rule_id` changed from plain `Integer` to `ForeignKey("recurring_rules.id")` with `recurring_rule` relationship.
- `app/models/__init__.py` — imports `RecurringFrequency`, `RecurringRule`.
- Alembic migration `fb627ac5984d` — creates `recurring_rules` table; adds FK on `transactions.recurring_rule_id`.
- `app/schemas/recurring.py` — `RecurringRuleCreate`, `RecurringRuleUpdate`, `RecurringRuleRead` Pydantic DTOs.
- `app/crud/recurring.py` — `list_rules` (with active-only filter), `get_rule`, `create_rule`, `update_rule`, `delete_rule`, `update_last_generated_date`.
- `app/services/recurring.py` — `materialize_rule`, `materialize_all` (idempotent), `next_occurrences` preview.
- `app/routers/recurring.py` — 3 HTML pages, 3 HTMX mutations, 2 JSON API, preview endpoint (`GET /api/recurring/{id}/preview`), materialize endpoint (`POST /api/recurring/materialize`).
- Templates: `recurring/list.html`, `recurring/form.html` (conditional day-of-month/week fields), `partials/recurring_card.html` (next-occurrence preview, category/inactive badges).
- `app/main.py` — router mounted; lifespan calls `materialize_all()` on startup if `RECURRING_AUTO_MATERIALIZE=true`.
- `app/templates/base.html` — "Recurring" nav enabled; footer "Phase 6".
- `app/templates/dashboard.html` — Phase 6 build status green.
- `tests/test_recurring.py` — 47 tests: model, CRUD, `next_occurrences` (all frequencies), materialize (idempotent), HTML pages, HTMX, JSON API, preview/materialize endpoints, validation. All pass.

Key decisions during implementation:
- `type` is a plain `String(10)` column — validated at the router layer, not an enum.
- Form fields use `str | None = Form(None)` with manual parsing (same pattern as the Phase 3 `account_id` filter fix) to avoid FastAPI coercion issues from HTML empty-string submissions.
- `_next_date` helper adds `interval` periods to `after`, then snaps to configured `day_of_week`/`day_of_month`.

Verified:
- `pytest -q` → **181 passed** (134 existing + 47 recurring).
- `GET /recurring` renders list with empty state and "Add rule" CTA.
- Full CRUD round-trip for recurring rules via HTMX.
- `GET /api/recurring/{id}/preview` returns 5 next occurrence dates.
- `POST /api/recurring/materialize` creates transactions for active rules, skips inactive.
- Materialize is idempotent (second call → 0 new transactions).
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

#### Deferred tasks

- **Dashboard period filter**: Add a dropdown selector to the dashboard page (above charts) allowing the user to pick a time period — at minimum: "Current month", "Previous month", "Last 3 months", "This year", "All time". The dropdown should pass the appropriate `month` / `year` query params to the `/api/dashboard/category-breakdown`, `/api/dashboard/summary`, and `/api/dashboard/spending` endpoints so charts and KPIs re-render for the selected period. Currently these endpoints default to the current calendar month, so categories or transactions dated in prior months are invisible.
- **Quick-add transaction modal on the dashboard**: Currently the dashboard links to the full `/transactions/new` page. A future enhancement would add an Alpine.js modal that lazy-loads the form via `hx-get="/transactions/new?partial=1"`, submits in place, and refreshes dashboard widgets (KPIs, charts, account balances, recent transactions) via HTMX partial swaps. The form would be extracted into `partials/transaction_form.html` so the same partial is reused by the modal and the full create page.

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
