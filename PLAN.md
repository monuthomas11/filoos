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
| (same for categories, budgets, recurring in future phases)                |

> POST/PATCH return `HX-Redirect` because the create/edit forms live on dedicated pages
> where the target element (`#account-list`, `#transaction-list`) does not exist.
> DELETE endpoints return 200 with `HX-Trigger: transaction-deleted` — the list page
> listens for this event and re-fetches the list.

### JSON API (used by Chart.js on the dashboard)

| Method | Path                                                   | Returns                  |
|--------|--------------------------------------------------------|--------------------------|
| GET    | `/api/transactions`                                    | list (filterable)        |
| GET    | `/api/transactions/{id}`                               | single transaction       |
| GET    | `/api/accounts/{id}/balance`                           | account balance          |
| GET    | `/api/dashboard/summary`                               | totals for current month |
| GET    | `/api/dashboard/spending?range=30d`                    | daily expense series     |
| GET    | `/api/dashboard/category-breakdown?month=YYYY-MM`      | category totals          |
| GET    | `/api/accounts/{id}/balance-history?range=90d`         | daily balance series     |
| GET    | `/api/predictions/expenses?horizon=30`                 | 7/30-day forecast + band |
| GET    | `/api/predictions/balance?horizon=90`                  | projected balance + band |
| GET    | `/api/budgets/status?month=YYYY-MM`                    | per-category progress    |
| POST   | `/api/recurring/materialize`                           | trigger materialization  |

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

## 9. Phased Roadmap

| # | Phase | Deliverable | Checkpoint |
|---|-------|-------------|------------|
| 1 | **Foundation** | Scaffold, FastAPI app, `config.py` with `DEFAULT_CURRENCY="INR"`, base template (Tailwind/HTMX/Alpine/Chart.js, dark-mode toggle), Alembic initialized, `.env.example`, `.gitignore`, `PLAN.md`, README, `dev.ps1`/`dev.sh` | `uvicorn` serves styled dashboard at <http://127.0.0.1:8000> |
| 2 | **Accounts** | `Account` model + migration, CRUD pages, HTMX form partials, validation, color/icon per account | Create cash + bank + credit card; balances on placeholder dashboard |
| 3 | **Transactions** | **done** | Ledger, transfers, filterable list, 29 tests |
| 4 | **Dashboard v1** | `services/analytics.py`, `/api/dashboard/*`, dashboard.html with total balance, per-account cards w/ sparkline, daily-spend bar, category donut, recent txns | All charts render from real data |
| 5 | **Categories & Budgets** | `Category`, `Budget` models + migrations, CRUD pages, budget progress bars on dashboard | Set ₹10,000 food budget; see progress on dashboard |
| 6 | **Recurring rules** | `RecurringRule` model + migration, `services/recurring.py` materializer, auto-run on startup, "next 5 occurrences" preview | Mark salary as monthly; see it auto-appear on the 1st |
| 7 | **Predictions** | `services/forecasting.py`, `/api/predictions/*`, balance projection chart w/ confidence band, 7/30-day expense forecast, runway warning | See projected balance 90 days out |
| 8 | **Polish** | pytest suite, README polish, free-hosting notes (Render/Railway/Fly), error pages, accessibility pass | Test suite green; project shareable |

> Note: `scripts/seed.py` was implemented ahead-of-schedule (post-Phase 3 bugfix session).
> It creates 4 accounts + 11 transaction rows with realistic INR amounts using Alembic.

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

In all cases, the deploy artifact is a small `Dockerfile` (to be added in Phase 8). For now, development is local-only.

## 12. Future-Proofing (no work now, but design allows it)

- **Multi-user**: add a `users` table and `user_id` FK on every model; switch `deps.get_current_user` from no-op to real session auth.
- **Multi-currency**: per-account `currency` is already in the schema; just add an FX rate cache and conversion in the analytics layer.
- **Import / receipts**: `attachments` table; HTMX file upload is trivial with the existing stack.
- **Production CSS**: switch from Tailwind Play CDN to a compiled `app.css` via the Tailwind standalone CLI or a one-shot build script.

## 13. Open Considerations

- Tagging on transactions (e.g. `#business`)? Defer to v2 unless requested.
- Net-worth tracking across investment accounts? Track in `accounts` table; no separate net-worth model needed.
- "Shared" expenses (split with a partner)? Out of scope for v1.
- Mobile responsiveness - dashboard grid will use Tailwind responsive classes; deep mobile UX in a future pass.

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
