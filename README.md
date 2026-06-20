# FutureFunds

A personal expense tracker with a lightweight, beautiful dashboard and balance predictions.

- **Stack**: Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, SQLite, Jinja2, HTMX, Alpine.js, Tailwind CSS, Chart.js
- **Forecasting**: lightweight statistics (exponential moving average + day-of-week seasonality + linear trend, with confidence bands)
- **Currency**: configurable (default **INR**)
- **Mode**: multi-user with Google SSO (each user sees only their own data)
- **Theme**: clean neutral slate/indigo, light & dark mode

See [`PLAN.md`](./PLAN.md) for the full design, architecture, and phased roadmap, and [`STATUS.md`](./STATUS.md) for a quick snapshot of the current phase and what's next.

## Build status

| Phase | Status | Notes |
|---|---|---|---|---|
| 1. Foundation | done | Scaffold, FastAPI app, base template, dark mode, Alembic wired, dev scripts, smoke tests (3/3 passing) |
| 2. Accounts | done | Model, CRUD, HTMX forms, page list, dashboard cards, JSON API, 24 tests |
| 3. Transactions | done | Model, CRUD, HTMX forms, filterable list, transfer flow, 47 tests |
| 4. Dashboard v1 | done | Analytics service, JSON API, Chart.js charts (daily-spend bar, category donut), monthly KPIs, 18 tests |
| 5. Categories & Budgets | done | Category CRUD, budget progress bars, 45 tests (21 categories + 24 budgets) |
| 6. Recurring rules | done | Model, CRUD, materializer, next-occurrences preview, 36 tests |
| 7. Predictions | done | Forecasting engine (EMA + day-of-week seasonality + confidence bands), balance projection chart, runway warning, 22 tests |
| 8. Polish | done | Dashboard period filter, seed hardening, error pages, a11y, compiled Tailwind, deploy notes |
| 9. Auth (Google SSO) | done | Google OAuth login, session-based auth, per-user data isolation, profile header, sign-out button |

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

Then open <http://127.0.0.1:8000>. You'll be redirected to the login page.

### Google OAuth setup

To enable sign-in, create OAuth 2.0 credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select existing)
3. **APIs & Services > OAuth consent screen** — choose **External**, fill app name/email
4. **APIs & Services > Credentials** — **Create Credentials > OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: `http://127.0.0.1:8000/auth/google/callback`
5. Copy the **Client ID** and **Client Secret**

Add to your `.env` file (at project root):

```
FF_GOOGLE_CLIENT_ID=your-client-id
FF_GOOGLE_CLIENT_SECRET=your-client-secret
FF_SESSION_SECRET=any-random-secret-string
```

Restart the server. "Sign in with Google" will work. In **Testing** mode, add test users in the OAuth consent screen.

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
|---|---|
| `GET /` | Dashboard (real balances, recent transactions, Chart.js charts, budget progress) |
| `GET /login` | Login page (Sign in with Google) |
| `GET /auth/login` | Redirects to Google OAuth consent screen |
| `GET /auth/google/callback` | OAuth callback — upserts user, sets session, redirects to `/` |
| `POST /auth/logout` | Clears session, redirects to `/login` |
| `GET /accounts` | Account list (CRUD) |
| `GET /transactions` | Transaction list (filterable) |
| `GET /categories` | Category list (CRUD) |
| `GET /budgets` | Budget list (CRUD) with progress bars |
| `GET /recurring` | Recurring rule list (CRUD) with next-occurrence preview |
| `GET /healthz` | Liveness probe (`{"status":"ok","app":"FutureFunds"}`) |
| `GET /docs` | Auto-generated OpenAPI docs for the JSON API |
| `GET /static/*` | CSS / JS / assets |
| `GET /api/dashboard/summary` | Monthly income/expense/savings-rate KPIs |
| `GET /api/dashboard/spending` | Daily expense series for Chart.js |
| `GET /api/dashboard/category-breakdown` | Breakdown by category |
| `GET /api/dashboard/budgets` | Budget progress data |
| `GET /api/recurring` | Recurring rule list (JSON) |
| `GET /api/recurring/{id}/preview` | Next 5 occurrence dates |
| `POST /api/recurring/materialize` | Trigger manual materialization |
| `GET /api/accounts/{id}/balance-history` | Daily running balance per account |

## Project layout

```
FutureFunds/
├── backend/
│   ├── app/             # FastAPI application package
│   │   ├── main.py      # App factory, routes, lifespan
│   │   ├── config.py    # pydantic-settings (.env aware)
│   │   ├── database.py  # SQLAlchemy engine, Base, session
│   │   ├── deps.py      # FastAPI dependencies (get_current_user)
│   │   ├── models/      # ORM models (User, Account, Transaction, etc.)
│   │   ├── schemas/     # Pydantic DTOs
│   │   ├── crud/        # DB operations
│   │   ├── routers/     # Page + API + auth routers
│   │   ├── services/    # Business logic
│   │   ├── templates/   # Jinja2 (base, dashboard, login, partials)
│   │   └── static/      # CSS, JS
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

- **No build step in dev.** Tailwind CSS is loaded via the official Play CDN during development. For production, compile via `scripts/build_css.sh` (uses `backend/tailwind.config.js`).
- **HTMX** powers form submissions and partial updates.
- **Alpine.js** handles the dark-mode toggle and small UI state.
- **Chart.js** powers the dashboard charts (daily spending bar, category breakdown doughnut) with data fetched from the JSON API.
- Dark mode persists per browser via `localStorage`.

## Development scripts

- `scripts/dev.ps1` / `scripts/dev.sh` - one-shot dev launcher (venv, deps, migrations, uvicorn)
- `scripts/seed.py` - seed demo data (4 accounts, 11 transaction rows with INR amounts)
- `scripts/build_css.sh` - compile Tailwind CSS for production (requires `tailwindcss` CLI on PATH)

## Deployment

FutureFunds ships as a single FastAPI process backed by a SQLite file. The included `Dockerfile` packages the app for container-based hosting.

### Build and run

```bash
docker build -t futurefunds .
docker run -p 8000:8000 -v "$(pwd)/data:/app/data" futurefunds
```

The `-v` mount persists the SQLite database outside the container. Without it, all data is lost on restart.

### Free hosting options

| Platform | Notes |
|---|---|
| **Render** | Web Service + persistent disk. Set start command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add `data/` to the disk mount. |
| **Railway** | Similar to Render. Use the Dockerfile directly. Ephemeral disk resets on restart — mount a persistent volume for the SQLite file. |
| **Fly.io** | Dockerfile works as-is. Add a `fly.toml` with `[mounts] source=data, destination=/app/data` for persistent storage. |

### Production CSS

Development uses the Tailwind Play CDN for zero-config iteration. For production, compile the stylesheet:

```bash
# 1. Download tailwindcss CLI from https://tailwindcss.com/blog/standalone-cli
# 2. Place it on PATH
# 3. Run:
./scripts/build_css.sh
```

Then swap the CDN `<script>` in `base.html` with `<link rel="stylesheet" href="{{ url_for('static', path='css/app.compiled.css') }}" />`.

## License

MIT
