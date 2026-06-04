# FutureFunds

A personal expense tracker with a lightweight, beautiful dashboard and balance predictions.

- **Stack**: Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, SQLite, Jinja2, HTMX, Alpine.js, Tailwind CSS, Chart.js
- **Forecasting**: lightweight statistics (exponential moving average + day-of-week seasonality + linear trend, with confidence bands)
- **Currency**: configurable (default **INR**)
- **Mode**: local-first, single user
- **Theme**: clean neutral slate/indigo, light & dark mode

See [`PLAN.md`](./PLAN.md) for the full design, architecture, and phased roadmap, and [`STATUS.md`](./STATUS.md) for a quick snapshot of the current phase and what's next.

## Build status

| Phase | Status | Notes |
|---|---|---|---|
| 1. Foundation | done | Scaffold, FastAPI app, base template, dark mode, Alembic wired, dev scripts, smoke tests (3/3 passing) |
| 2. Accounts | done | Model, CRUD, HTMX forms, page list, dashboard cards, JSON API, 20 tests |
| 3. Transactions | done | Model, CRUD, HTMX forms, filterable list, transfer flow, 29 tests |
| 4. Dashboard v1 | done | Analytics service, JSON API, Chart.js charts (daily-spend bar, category donut), monthly KPIs, 16 tests |
| 5. Categories & Budgets | pending | Category CRUD, budget progress |
| 6. Recurring rules | pending | Auto-materialize on startup |
| 7. Predictions | pending | EMA + seasonality + confidence bands |
| 8. Polish | pending | Tests, seed data, deploy notes |

## Quick start

The one-shot dev launcher creates a venv, installs deps, applies migrations, and starts the server with auto-reload.

```powershell
# Windows
.\scripts\dev.ps1
```

```bash
# macOS / Linux
./scripts/dev.sh
```

Then open <http://127.0.0.1:8000>.

### Manual setup

```bash
# from the project root
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"

# Initialize the database (no-op until the first real migration lands in Phase 2)
alembic upgrade head

# Run the dev server
uvicorn app.main:app --reload
```

### Seed demo data

```bash
# from the project root (with backend/.venv activated)
python scripts/seed.py
```

Creates 4 accounts (Wallet, HDFC Bank, SBI Savings, Axis Credit Card) and 11 transaction rows with realistic INR amounts. Applies Alembic migrations automatically.

### Run the tests

```bash
# from backend/ (with the venv activated)
pytest
```

## Endpoints (current)

| Path | Purpose |
|---|---|---|
| `GET /` | Dashboard (real balances, recent transactions, Chart.js charts) |
| `GET /accounts` | Account list (CRUD) |
| `GET /transactions` | Transaction list (filterable) |
| `GET /healthz` | Liveness probe (`{"status":"ok","app":"FutureFunds"}`) |
| `GET /docs` | Auto-generated OpenAPI docs for the JSON API |
| `GET /static/*` | CSS / JS / assets |
| `GET /api/dashboard/summary` | Monthly income/expense/savings-rate KPIs |
| `GET /api/dashboard/spending` | Daily expense series for Chart.js |
| `GET /api/dashboard/category-breakdown` | Breakdown by type (categories in Phase 5) |
| `GET /api/accounts/{id}/balance-history` | Daily running balance per account |

## Project layout

```
FutureFunds/
├── backend/
│   ├── app/             # FastAPI application package
│   │   ├── main.py      # App factory, routes, lifespan
│   │   ├── config.py    # pydantic-settings (.env aware)
│   │   ├── database.py  # SQLAlchemy engine, Base, session
│   │   ├── deps.py      # FastAPI dependencies
│   │   ├── models/      # ORM models (populated per phase)
│   │   ├── schemas/     # Pydantic DTOs (per phase)
│   │   ├── crud/        # DB operations (per phase)
│   │   ├── routers/     # Page + API routers (per phase)
│   │   ├── services/    # Business logic (per phase)
│   │   ├── templates/   # Jinja2 (base, dashboard, partials)
│   │   └── static/      # CSS, JS, future assets
│   ├── alembic/         # Database migrations
│   ├── tests/           # pytest suite
│   ├── pyproject.toml
│   └── requirements.txt
├── data/                # SQLite database (gitignored)
├── scripts/             # dev.ps1, dev.sh, seed.py, build_css.sh
├── PLAN.md              # Living design document
├── STATUS.md            # Phase snapshot / handoff doc
└── README.md
```

## Frontend notes

- **No build step.** Tailwind CSS is loaded via the official Play CDN for v1; a compiled stylesheet is planned for production (`scripts/build_css.sh` is a placeholder for the standalone Tailwind CLI).
- **HTMX** powers form submissions and partial updates.
- **Alpine.js** handles the dark-mode toggle and small UI state.
- **Chart.js** powers the dashboard charts (daily spending bar, category breakdown doughnut) with data fetched from the JSON API.
- Dark mode persists per browser via `localStorage`.

## Development scripts

- `scripts/dev.ps1` / `scripts/dev.sh` - one-shot dev launcher (venv, deps, migrations, uvicorn)
- `scripts/seed.py` - seed demo data (4 accounts, 11 transaction rows with INR amounts)
- `scripts/build_css.sh` - placeholder for compiled Tailwind output

## License

MIT
