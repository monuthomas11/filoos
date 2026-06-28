# AGENTS.md — Filoos

Personal expense tracker. FastAPI + SQLAlchemy 2 + Alembic + SQLite/Postgres + Jinja2 + HTMX + Alpine.js + Tailwind CSS + Chart.js.

## Quick commands

```powershell
# Dev server (creates venv, installs deps, runs migrations, starts uvicorn)
.\scripts\dev.ps1

# Run tests (from backend/)
cd backend && pytest

# Lint (from backend/)
ruff check .

# Seed demo data (from project root)
python scripts/seed.py

# Create migration (from backend/)
alembic revision --autogenerate -m "description"

# Apply migrations (from backend/)
alembic upgrade head
```

No separate typecheck or formatter commands — ruff handles both linting and formatting.

## Architecture gotchas

**Multi-user isolation is mandatory.** Every CRUD function accepts `user_id` and scopes queries. `deps.get_current_user` reads from session cookie. Never bypass this — even in tests, a default user is created and overridden via `app.dependency_overrides[get_current_user]`.

**HTMX forms use `HX-Redirect`, not partials.** POST/PATCH on dedicated form pages (`/accounts/new`, `/transactions/{id}/edit`) return `Response(headers={"HX-Redirect": "/accounts"})` because the target elements (`#account-list`, `#transaction-list`) don't exist on those pages. DELETE returns 200 with `HX-Trigger` — the list page re-fetches via HTMX.

**Form data, not JSON.** HTMX forms submit `application/x-www-form-urlencoded`. Use `Form()` in FastAPI, not `Body()`. For PATCH endpoints, use `Optional[Form(None)]` with a filtered dict to avoid writing `None` into NOT NULL columns.

**Amounts are signed.** `Transaction.amount` is +income, -expense. Form input is always positive; the router applies the sign based on `type`.

**Transfers = two rows.** No separate transfers table. Two `transactions` rows share a `transfer_pair_id`.

## Testing patterns

- Fixtures live in `backend/tests/conftest.py`
- `tmp_db_path` — temp SQLite file per test (not in-memory, because TestClient threading)
- `client` — FastAPI TestClient with `get_db` and `get_current_user` overridden
- `db_session` — raw SQLAlchemy session for CRUD tests
- `anon_client` — for auth tests (real session middleware, no user override)
- Tests use `Base.metadata.create_all`, not Alembic migrations
- Run a single test: `pytest tests/test_accounts.py::test_create_account -v`

## Database

- SQLite locally (`data/expenses.db`, gitignored)
- Postgres in production (Neon.tech)
- `config.py` auto-rewrites bare `postgresql://` to `postgresql+psycopg://`
- `database.py` sets `pool_pre_ping` and `pool_recycle` when not SQLite
- Alembic `env.py` uses `render_as_batch=True` (SQLite ALTER support)
- All migrations must be created from `backend/` directory

## Conventions

- Package layout: `models/` → `schemas/` → `crud/` → `routers/` → `services/`
- Naming: snake_case files/functions, PascalCase classes, `XxxCreate`/`XxxUpdate`/`XxxRead` for Pydantic DTOs
- HTMX partials: `partials/<thing>_<action>.html`
- Design tokens: `accent-600` (indigo), `positive-600` (emerald), `negative-600` (red), `rounded-lg`, system font, shadow-sm on hover
- Dark mode via Tailwind `dark:` variant + Alpine.js toggle persisted in `localStorage`

## Deployment

- `Dockerfile` at repo root: multi-stage build (Node for Tailwind CSS, Python for runtime)
- Render blueprint: `render.yaml` at repo root
- Migrations run in Dockerfile CMD: `alembic upgrade head && uvicorn ...`
- `FF_ALLOWED_HOSTS` and `FF_GOOGLE_REDIRECT_URI` must match the real hostname exactly
- `FF_CURRENCY_SYMBOL` must be literal UTF-8 in `.env` (not `\u20b9` — pydantic-settings doesn't decode escapes)

## Env vars

All prefixed with `FF_`. Legacy unprefixed names still work but will be removed. Key vars: `FF_APP_ENV`, `FF_DATABASE_URL`, `FF_SESSION_SECRET`, `FF_GOOGLE_CLIENT_ID`, `FF_GOOGLE_CLIENT_SECRET`, `FF_ALLOWED_HOSTS`.

## Key files

| File | What it does |
|---|---|
| `backend/app/main.py` | App factory, middleware, routers, error handlers |
| `backend/app/config.py` | pydantic-settings, reads `.env`, legacy var migration |
| `backend/app/database.py` | SQLAlchemy engine, session factory, `get_db`, `session_scope` |
| `backend/app/deps.py` | `get_current_user`, `get_current_user_with_db` |
| `backend/tests/conftest.py` | Test fixtures (`client`, `db_session`, `anon_client`) |
| `scripts/dev.ps1` | One-shot dev launcher (Windows) |
| `scripts/seed.py` | Demo data seeder (accounts, transactions, recurring rules) |
| `deployment.md` | Full deployment plan (Render + Neon) |

## Design Context

Designed visual system lives in `PRODUCT.md` (strategic: register, users, brand personality, principles) and `DESIGN.md` (visual: colors, typography, elevation, components, do's/don'ts). Read both before any frontend work.

North Star: **"The Friendly Teller"** — warm, approachable, conversational finance. Single indigo accent, semantic green/red for income/expense only. 12px corner rounding, system font stack. |
