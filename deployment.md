# FutureFunds v1 — Deployment Plan

> **Audience:** the maintainer, deploying FutureFunds to a public URL on
> Render (web host) backed by Neon.tech Postgres (managed database).
> Companion to `README.md`, `PLAN.md`, and `STATUS.md`.
>
> **Status (2026-06-21):** Phase 1 (C1–C6) and Phase 2 (Google SSO +
> per-user data isolation) are ✅ complete — see §2 for what landed
> and §7 for the checklist. **Next up: Phase 3 (Render + Neon
> deployment).** The previous plan targeted GCP e2-micro + Cloudflare
> Tunnel; that has been replaced with the simpler managed-platform
> stack below. The Phase 1/2 changes are platform-agnostic and need
> no rework.

---

## 0. TL;DR

- **Host:** Render Web Service (Free tier) — `uvicorn` on a Docker
  image built from the repo's existing `Dockerfile`.
- **Database:** Neon.tech Postgres (Free tier) — serverless, scales to
  zero, 0.5 GB storage, 7-day point-in-time recovery included.
- **App:** same single FastAPI container; the database driver and
  `FF_DATABASE_URL` change, nothing else.
- **Network:** Render provides HTTPS automatically for the
  `*.onrender.com` subdomain (and for any custom domain you point at
  it via CNAME). No tunnel, no firewall, no origin certificate.
- **DNS + SSL:** handled by Render (auto-issued Let's Encrypt cert,
  auto-renewed). For a custom domain, add a CNAME in your DNS and
  Render provisions the cert.
- **Auth:** Google SSO via OAuth 2.0 — unchanged from Phase 2.
- **Backups:** Neon PITR (7-day retention, free tier) + a weekly
  logical `pg_dump` snapshot to local Render disk for paranoia.
- **Migrations:** run automatically as the Render **release command**
  on every deploy (`alembic upgrade head`); a failing migration
  blocks the deploy.
- **Estimated work:** ~1 day of focused effort across two phases
  (down from ~2.25 days for the VM plan, because Render + Neon
  remove almost all ops work).

---

## 1. Why this stack

| Choice | Reason |
|---|---|
| Render Web Service (Free) | Zero-ops: build from Git, auto-SSL, auto-deploy, no VM to patch. Docker runtime is supported, so our existing `Dockerfile` is reused. |
| Docker (not bare-metal Python) | Same as before — mirrors the `Dockerfile` already in repo, easy rollback via image tags. Render builds the image during deploy. |
| Neon.tech Postgres (Free) | Real RDBMS: proper transactions, concurrent writes, JSON columns, real constraints, full-text search if we ever want it. 0.5 GB is ample for a personal-finance workload. PITR + branching are free. |
| Connection pool tuned for serverless | Neon closes idle connections aggressively, so the engine uses `pool_pre_ping=True` + `pool_recycle=300`; a pooled endpoint (host contains `-pooler`) is used for the web service. |
| Render-native HTTPS | No Cloudflare tunnel, no `cloudflared`, no origin cert, no `--no-address` VM. Render terminates TLS at its edge and reverse-proxies to the container. |
| Render release command for migrations | `alembic upgrade head` runs before the new version goes live. A failed migration blocks the deploy — no half-migrated states. |
| Google SSO via `authlib` | Unchanged from Phase 2. |
| Multi-user data isolation | Unchanged from Phase 2. |

What this stack **doesn't** do (vs. the previous GCP+Cloudflare plan):

- **No Cloudflare.** Render's edge is sufficient for a low-traffic
  personal app; Cloudflare's WAF/CDN is overkill here.
- **No persistent disk on the app server.** The database is its own
  managed service. If we ever need file uploads, we'll add Render
  Persistent Disk (paid) or S3.
- **No always-on process.** Render's free tier sleeps the service
  after 15 min of inactivity — the next request pays a ~30 s cold
  start. Acceptable for a personal app; documented in §5.
- **No cron on free tier.** Render's free plan doesn't support cron
  jobs. Recurring-rule materialization was already moved off
  startup (Phase 2 — runs on demand via API), so this is fine.
  Nightly in-process `pg_dump` runs from a separate one-off Render
  service or a GitHub Action (see §5.2).

---

## 2. Critical blockers fixed in Phase 1 — ✅ DONE (2026-06-19)

All six items in this phase are implemented and verified. The build
succeeds, the app serves compiled CSS, logs are structured, and both
`/healthz` and `/readyz` are live. **Phase 2 (SSO + multi-user) is the
next thing to do.**

The subsections below show the *originally proposed* fix; the
"**Status / what landed**" block under each item records what was
actually merged and where.

### C1. `Dockerfile` references a missing `requirements.txt` — ✅ DONE

**File:** `Dockerfile` (root).

The current `Dockerfile` does `COPY requirements.txt .` but only
`backend/requirements.txt` exists. Build fails with "file not found".

**Original fix proposal (wheel-based two-stage Python build):**
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels \
    -r /app/requirements.txt && rm -rf /wheels
COPY backend/ ./
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Status / what landed:** Multi-stage build, but `node:20-alpine` is the
builder (so the final image has no Python toolchain artifacts and no
Tailwind tooling — saving ~150 MB vs. the original plan):

```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS css-builder       # builds Tailwind bundle, then thrown away
WORKDIR /build
COPY backend/package.json backend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY backend/tailwind.config.js ./
COPY backend/app/templates/ ./app/templates/
COPY backend/app/static/css/app.css ./app/static/css/app.css
RUN npx tailwindcss --config tailwind.config.js \
        --input app/static/css/app.css \
        --output app/static/css/app.compiled.css --minify

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=css-builder /build/app/static/css/app.compiled.css \
                      /app/app/static/css/app.compiled.css
RUN mkdir -p /app/data && useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

Notes:
- `--proxy-headers --forwarded-allow-ips *` is required for the
  X-Forwarded-* headers that Render sets on its reverse proxy to be
  honored (otherwise HTTPS detection from `request.url.scheme` is
  wrong). This was originally written for Cloudflare; the same flag
  works for Render.
- `app.compiled.css` is **not** copied from source — it comes from the
  builder stage. `app.compiled.css` and `node_modules/` are gitignored.

### C2. `.dockerignore` (new) — ✅ DONE

**File:** `.dockerignore` (new, repo root). Excludes `.git`, `.venv`,
`.env`, `data/*.db`, IDE files, Python caches, `node_modules/`,
`app.compiled.css`, and all top-level `*.md` (README, STATUS, PLAN,
REVIEW_CHANGES, deployment). Original list was simpler; the actual file
also covers `backend/.bin/`, `backend/app/static/css/app.compiled.css`,
and the project-management directories (`.claude/`, `.opencode/`,
`plans/`).

### C3. `.env.example` fix — ✅ DONE (partial)

**File:** `.env.example`.

**Status / what landed:** Currency escape fixed (`\u20b9` → literal `₹`)
and `FF_DEBUG=false` flipped. **SSO / session keys are now included**
(Google SSO implemented in Phase 2/9).

Current state (will be updated in Phase 3 to point at Postgres — see §4.6):
```ini
FF_APP_NAME=FutureFunds
FF_APP_ENV=production
FF_DEBUG=false
FF_DATABASE_URL=sqlite:////app/data/expenses.db
FF_DEFAULT_CURRENCY=INR
FF_CURRENCY_SYMBOL=₹
FF_FORECAST_HISTORY_DAYS=180
FF_FORECAST_CACHE_TTL_SECONDS=300
# FF_RECURRING_AUTO_MATERIALIZE=false

# Sessions / Auth
FF_SESSION_SECRET=change-me
FF_SESSION_MAX_AGE_SECONDS=86400
# FF_SESSION_COOKIE_SECURE=true

# Google OAuth
FF_GOOGLE_CLIENT_ID=
FF_GOOGLE_CLIENT_SECRET=
# FF_GOOGLE_REDIRECT_URI=

# Security
FF_ALLOWED_HOSTS=localhost,127.0.0.1
```

### C4. Compiled Tailwind CSS — ✅ DONE

**Files:** `backend/app/templates/base.html`, `backend/app/static/css/app.css`,
`backend/app/static/css/app.compiled.css` (generated, gitignored),
`backend/tailwind.config.js`, `backend/package.json`,
`scripts/build_css.sh`, `Dockerfile` (builder stage).

**Status / what landed:**
- `app.css` was updated to include the required `@tailwind base; @tailwind components; @tailwind utilities;` directives at the top — without these, the build silently emits only the override CSS (440 B) and no utilities. **This is the gotcha that bit the first attempt.**
- `app.compiled.css` is 19.7 KB, includes Tailwind preflight + all utilities used across the 20 templates (verified: `bg-accent-500/10`, `bg-negative-500/10`, `bg-positive-500/10`, `text-positive-600`, `text-negative-600`, `hover:*`, `dark:*`, `focus-visible:*`, `sm:`, `md:`, `lg:` breakpoints).
- `base.html` no longer references `cdn.tailwindcss.com`; only loads `app.compiled.css`.
- `package.json` declares `tailwindcss ^3.4.17` as a devDep; `package-lock.json` is committed (34.6 KB) so `npm ci` is reproducible.
- `scripts/build_css.sh` was improved to (1) download the standalone Tailwind CLI binary as a fallback for environments without Node, (2) fall back to `node_modules/.bin/tailwindcss`, then (3) fall back to a PATH `tailwindcss`.
- `.gitignore` excludes `backend/node_modules/`, `backend/.bin/`, `backend/app/static/css/app.compiled.css`.

### C5. `FF_DEBUG` off + structured logging — ✅ DONE (extended)

**Files:** `backend/app/logging_config.py` (new), `backend/app/main.py`,
`backend/app/config.py`, `backend/app/services/recurring.py`.

**Status / what landed:** More than the proposal. Implemented:

1. `app/logging_config.py` with two custom formatters:
   - `JsonFormatter` for production — one-line JSON per record with `time`/`level`/`logger`/`msg` and any `extra={}` fields. Parseable by Render's log viewer, `journalctl`, and Loki out of the box.
   - `DevFormatter` for development — plain text with `extra={}` fields appended as `key=value` pairs.
2. `FF_LOG_LEVEL` setting (default `DEBUG` in dev, `INFO` in prod/test).
3. Uvicorn loggers are reconfigured to propagate through our root handler, so access logs share the same format.
4. `sqlalchemy.engine`, `urllib3.connectionpool`, `httpx` pinned to `WARNING` to keep noise down.
5. Request-logging middleware in `main.py` logs one line per request with `request_id` (12-char hex, also returned in `x-request-id` response header), `method`, `path`, `status`, `elapsed_ms`. Unhandled exceptions are logged via `logger.exception` and re-raised.
6. Lifespan logs at startup: configuration, version, env, recurring-materialization summary.
7. `services/recurring.py` logs per-rule results (INFO if materialized, DEBUG if up-to-date) and catches+logs per-rule failures so one bad rule doesn't abort the loop.
8. Error handler logs unhandled exceptions via `logger.exception`.

Sample dev output:
```
2026-06-19T23:46:27+0530 [INFO] app: logging configured  env='development' level='DEBUG'
2026-06-19T23:46:27+0530 [INFO] app.services.recurring: materializing recurring rules  rule_count=2
2026-06-19T23:46:27+0530 [DEBUG] app.services.recurring: recurring rule up to date  rule_id=1 rule_description='Monthly Salary'
2026-06-19T23:46:27+0530 [INFO] app: recurring materialization complete  rules=2 generated=0
2026-06-19T23:46:58+0530 [INFO] app: request  request_id='f4f252552e12' method='GET' path='/healthz' status=200 elapsed_ms=182.78
```

Logs go to **stdout only** (no file handler). Captured by Render's log viewer automatically.

### C6. `/_healthz` vs `/readyz` — ✅ DONE

**File:** `backend/app/main.py`.

**Status / what landed:** Split exactly as proposed, with the `db`
parameter switched to `session_scope()` context manager (matches the
project's existing session pattern) and a `settings` sanity check added:

```python
@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}

@app.get("/readyz")
async def readyz(response: Response) -> dict[str, str]:
    checks: dict[str, str] = {}
    healthy = True
    try:
        with session_scope() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except SQLAlchemyError as exc:
        healthy = False
        checks["database"] = f"error: {exc.__class__.__name__}"
        logger.error("readiness check: database unreachable", exc_info=exc)
    checks["settings"] = "ok" if settings.app_name else "missing"
    if not settings.app_name:
        healthy = False
    response.status_code = 200 if healthy else 503
    return {"status": "ok" if healthy else "degraded", **checks}
```

Verified live: `/healthz` → 200 `{"status":"ok","app":"FutureFunds"}`,
`/readyz` → 200 `{"status":"ok","database":"ok","settings":"ok"}`.

**Also fixed during C5/C6 verification:** `tests/test_config.py::test_settings_legacy_env_vars_backward_compatibility` was broken — it patched `os.environ` but the project's `.env` file was still loaded by pydantic-settings, so the FF_ values from `.env` always won. Fixed by passing `_env_file=None` to isolate the test. **Pre-existing bug, not caused by C5.**

---

## 3. Phase 2 — Google SSO + multi-user data isolation — ✅ DONE

Any Google account can sign in, but every row is scoped by `user_id`,
so users never see each other's data.

### 3.1 New `User` model

**File:** `backend/app/models/user.py` (new).

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_login_at: Mapped[datetime | None]
```

### 3.2 New migration

**File:** `backend/alembic/versions/<ts>_add_users_and_user_id_columns.py`.

Creates `users` table and adds nullable `user_id` FK to
`accounts`, `categories`, `budgets`, `recurring_rules`, `transactions`.

### 3.3 New auth router

**File:** `backend/app/routers/auth.py` (new).

- `GET /auth/login` → 302 to Google OAuth consent screen.
- `GET /auth/google/callback` → exchange code, fetch userinfo,
  upsert `User`, set signed session cookie, redirect to `/`.
- `POST /auth/logout` → clear cookie, redirect to `/login`.

### 3.4 Dependencies

**File:** `backend/app/deps.py`.

```python
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, "Not signed in")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Stale session")
    return user

def get_current_user_with_db(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> tuple[Session, User]:
    return db, user
```

### 3.5 Scope all queries by `user_id`

**Files:** every `backend/app/crud/*.py`.

Each `list_*`, `get_*`, `create_*`, `update_*`, `delete_*` accepts
a `user_id` arg and adds `.where(Model.user_id == user_id)` (or the
equivalent JOIN through account_id → account.user_id).

### 3.6 Login page

**File:** `backend/app/templates/login.html` (new).

Single button: "Sign in with Google". Extends `base.html`.

### 3.7 Session middleware

**File:** `backend/app/main.py`.

```python
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)
app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "localhost"])
```

### 3.8 Tests

**File:** `backend/tests/test_auth.py` (new).

- Anonymous request → 401 or 302 to `/login`.
- Sign-in flow mocked via `authlib` test client.
- Session cookie presence/absence/signature.
- Logout clears cookie.
- Cross-user isolation: user A creates an account, user B's request
  returns 404 for that account.

---

## 4. Phase 3 — Render + Neon deployment

### 4.1 Architecture

```
  Visitor's browser
        |
        | HTTPS (public, auto-cert)
        v
  +---------------------+
  |  Render edge        |   <-- TLS termination, HTTP/2, gzip
  |  (anycast, auto)    |
  +---------------------+
        |
        | HTTPS on internal network
        v
  +---------------------+
  |  Web service        |   <-- Docker container, uvicorn :$PORT
  |  (yourapp.onrender  |       Cold-starts after 15 min idle
  |   .com)             |       on free tier (~30 s first req)
  +---------------------+
        |
        | Postgres over TLS (Neon pooled endpoint)
        v
  +---------------------+
  |  Neon Postgres      |   <-- serverless, auto-suspends
  |  (aws-us-east-2)    |       0.5 GB, 7-day PITR
  +---------------------+
```

What Render handles for us (no work on our side):
- TLS certificate (auto-issued for `*.onrender.com`, auto-renewed)
- HTTP/2, gzip, Brotli
- Health-check-driven rollout (waits for `/healthz` to return 200)
- Auto-rollback on failed health check
- Auto-deploy on push to the watched branch
- Log capture (stdout/stderr) with 7-day retention
- Secret env vars (encrypted at rest, masked in UI)

What Neon handles for us:
- Postgres install, patching, backups
- Connection encryption (TLS required by default on free tier)
- 7-day PITR (point-in-time recovery to the second)
- Branching (instant DB copies for schema experiments)
- Auto-suspend of compute when idle (saves the 191.9 hr/month quota)

### 4.2 One-time Neon setup

1. Sign up at <https://console.neon.tech> with GitHub.
2. **Create a project.** Pick a region. Recommendations:
   - If you're using the default Render region, pick the closest
     Neon region (Render free runs on AWS; Neon has `aws-us-east-1`,
     `aws-us-east-2`, `aws-us-west-2`, `aws-eu-central-1`, etc.).
   - Latency between Render and Neon matters for every request, so
     same-region is best.
3. **Create a database** (Neon creates a default `neondb` per
   project — you can keep it).
4. **Get the connection string.** Neon shows two endpoints on the
   dashboard:
   - Direct (host like `ep-xxxx.us-east-2.aws.neon.tech`):
     high-concurrency, no pooling, intended for long-lived
     processes.
   - **Pooled (host like `ep-xxxx-pooler.us-east-2.aws.neon.tech`):**
     PgBouncer-style transaction-mode pool. **Use this for the web
     service.** It's the right fit for a serverless web tier that
     opens many short-lived sessions.
5. **Save the password** — Neon shows it once at creation. If you
   lose it, rotate via the dashboard.
6. Note the **PITR retention** — 7 days on Free, 30 days on Launch.
   Free is fine for v1.

### 4.3 Code changes for Postgres (small, isolated) — ✅ DONE

These are the only code edits Phase 3 needs. Everything else is
config (env vars, render.yaml).

**C7. Add Postgres driver to `requirements.txt` — TODO (Phase 3)**

**File:** `backend/requirements.txt`.

Add (use psycopg v3 — actively maintained, smaller, async-ready):
```
psycopg[binary]>=3.1.18
```

**C8. Make `database.py` engine Postgres-aware — TODO (Phase 3)**

**File:** `backend/app/database.py`.

Changes:
- Drop the SQLite `check_same_thread` and the `PRAGMA foreign_keys`
  event listener when not using SQLite.
- Add `pool_pre_ping=True` and `pool_recycle=300` to recycle idle
  connections before Neon closes them server-side. With the pooled
  endpoint this is mostly belt-and-braces, but it makes direct
  connections safe too.
- Keep `ensure_data_dir()` as a no-op when `database_url` doesn't
  start with `sqlite:///`.

Sketch of the new engine block:
```python
_is_sqlite = _settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    future=True,
    echo=False,
    pool_pre_ping=not _is_sqlite,
    pool_recycle=300 if not _is_sqlite else -1,
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
```

**C9. Update `.env.example` for Postgres — TODO (Phase 3)**

**File:** `.env.example`. Replace the SQLite line with the
Postgres form. Keep a commented-out SQLite line for local dev:
```ini
# Database (Postgres on Neon).
# Use the POOLED endpoint (hostname includes -pooler) for the web service.
FF_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@ep-xxxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require

# Local dev (SQLite, relative to backend/):
# FF_DATABASE_URL=sqlite:///../data/expenses.db
```

**C10. Update `alembic/env.py` for Postgres — TODO (Phase 3, optional)**

`render_as_batch=True` is a no-op on Postgres (it's an SQLite-only
escape hatch), so leaving it in is harmless. **No change strictly
required.** If we want to clean it up:

```python
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),  # only when needed
    )
    ...
```

Skip for v1 — keep the existing version.

**C11. Make `Dockerfile` honor Render's `$PORT` — TODO (Phase 3)**

**File:** `Dockerfile`.

Render sets the `PORT` env var (defaults to 10000; we set 8000 in
`render.yaml` so the existing healthcheck on 8000 still works). The
current `CMD` is hard-coded to port 8000. Change it to:

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} \
      --proxy-headers --forwarded-allow-ips='*'"]
```

This keeps the existing behavior on the old GCP plan (defaults to
8000) and also works on Render.

### 4.4 `render.yaml` — Infrastructure as Code — ✅ DONE

**File:** `render.yaml` (new, repo root). Declarative service
definition; Render reads it when you "New → Blueprint" or push to a
connected repo.

```yaml
services:
  - type: web
    name: futurefunds
    runtime: docker
    plan: free
    region: oregon                # pick whatever is closest to Neon
    branch: main
    dockerfilePath: ./Dockerfile
    dockerContext: .
    healthCheckPath: /healthz
    autoDeploy: true
    envVars:
      - key: FF_APP_ENV
        value: production
      - key: FF_DEBUG
        value: "false"
      - key: FF_DATABASE_URL
        sync: false               # set in Render UI; secret
      - key: FF_SESSION_SECRET
        generateValue: true       # Render generates and stores
      - key: FF_SESSION_COOKIE_SECURE
        value: "true"
      - key: FF_ALLOWED_HOSTS
        value: "yourapp.onrender.com"
      - key: FF_GOOGLE_CLIENT_ID
        sync: false
      - key: FF_GOOGLE_CLIENT_SECRET
        sync: false
      - key: FF_GOOGLE_REDIRECT_URI
        value: "https://yourapp.onrender.com/auth/google/callback"
      - key: FF_DEFAULT_CURRENCY
        value: "INR"
      - key: FF_CURRENCY_SYMBOL
        value: "₹"
      - key: FF_LOG_LEVEL
        value: "INFO"
      - key: PORT
        value: "8000"             # Render injects $PORT; this is the
                                  # only way to make uvicorn listen on
                                  # it via the Dockerfile's CMD
    releaseCommand: "cd backend && alembic upgrade head"
    # startCommand is whatever the Dockerfile's CMD already runs.
    # We don't override it — the existing uvicorn line is correct.
```

Notes on the `render.yaml`:
- `releaseCommand` runs **before** the new container is exposed. If
  `alembic upgrade head` fails, the deploy is rolled back.
- We **don't** override `startCommand` — the Dockerfile `CMD` (updated
  in C11, §4.3) runs `uvicorn` with the right flags, including
  reading `$PORT` so it works on both Render and the old GCP plan.
- `FF_DATABASE_URL`, `FF_GOOGLE_CLIENT_ID`, `FF_GOOGLE_CLIENT_SECRET`
  are `sync: false` (set in the Render dashboard as "Secret" env
  vars) because they contain secrets that shouldn't be in the
  blueprint file even though the dashboard encrypts them at rest.

### 4.5 First deploy

1. Push the changes from §4.3 and §4.4 to `main`.
2. In Render dashboard → **New → Blueprint** → point at the repo.
3. Render parses `render.yaml` and creates the `futurefunds` web
   service. The first build takes a few minutes (compiles Tailwind
   + installs Python deps).
4. Set the secret env vars in the dashboard:
   - `FF_DATABASE_URL` = the pooled Neon connection string
   - `FF_GOOGLE_CLIENT_ID` = from Google Cloud Console
   - `FF_GOOGLE_CLIENT_SECRET` = from Google Cloud Console
5. The `releaseCommand` runs `alembic upgrade head` against Neon,
   applying all migrations from scratch on the empty database.
6. The container starts. Render waits for `GET /healthz` to return
   200 and the build turns green.
7. Visit `https://yourapp.onrender.com/login` and sign in.

### 4.6 Google OAuth setup

In **Google Cloud Console → APIs & Services → Credentials → OAuth 2.0
Client IDs**, update the **Authorized redirect URIs**:

```
https://yourapp.onrender.com/auth/google/callback
```

(Add this alongside any local dev URI like
`http://localhost:8000/auth/google/callback`.)

The `FF_GOOGLE_REDIRECT_URI` env var in Render must match exactly —
including the scheme, host, and path.

### 4.7 Custom domain (optional, free on Render)

1. Render dashboard → service → **Settings → Custom Domains →
   Add**.
2. Enter `expenses.yourdomain.com` (or whatever). Render shows the
   required CNAME target.
3. In your DNS provider, add:
   ```
   expenses.yourdomain.com  CNAME  yourapp.onrender.com
   ```
4. Render auto-provisions a Let's Encrypt cert (takes ~30 s).
5. Update `FF_ALLOWED_HOSTS` and `FF_GOOGLE_REDIRECT_URI` in Render
   to use the new domain. Save. Render re-deploys automatically.

### 4.8 Health checks on Render

- Render hits `healthCheckPath: /healthz` every few seconds after
  the container starts. The first 200 response marks the deploy
  successful.
- `/healthz` does **not** touch the database (intentionally — it
  must be fast and survive transient DB blips so Render doesn't
  roll back a healthy container).
- `/readyz` is kept for external probes (UptimeRobot, etc.) that
  care about the database.

### 4.9 Local development with Postgres

If you want to mirror prod locally:

```bash
# .env (local, gitignored)
FF_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@ep-xxxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
```

Local dev can keep using SQLite (just point `FF_DATABASE_URL` at
`sqlite:///../data/expenses.db`) — the engine switches transparently
based on the URL scheme. This is the same switch the existing
`database.py` already does (`startswith("sqlite")`).

---

## 5. Phase 4 — Backups + monitoring

### 5.1 Neon PITR (primary backup)

Neon automatically retains a 7-day write-ahead log on the Free tier.
To restore:

1. Neon console → project → **Restore** → pick a timestamp.
2. Confirm. Neon creates a new branch from that point in time.
3. Promote that branch to primary if you want it to be the new
   production database (cuts the app over with a config change).

This covers accidental data corruption, "I deleted the wrong
account" mistakes, and most forms of "I broke the schema and rolled
back".

### 5.2 Weekly logical backup (belt-and-braces)

Render's free tier does **not** support cron jobs, and PITR alone
covers the data plane but not a "Neon project accidentally deleted"
scenario. Add a one-off Render service that runs `pg_dump` on a
schedule via GitHub Actions (free, 2 000 minutes/month):

**File:** `.github/workflows/pg-backup.yml` (new):

```yaml
name: weekly-pg-backup
on:
  schedule:
    - cron: "0 3 * * 0"   # Sunday 03:00 UTC
  workflow_dispatch:        # manual trigger from the Actions tab

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install psql client
        run: sudo apt-get install -y postgresql-client
      - name: Dump Neon database
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
        run: |
          ts=$(date -u +%Y%m%dT%H%M%SZ)
          pg_dump "$DATABASE_URL" --no-owner --no-acl \
            --file="futurefunds-${ts}.sql"
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: futurefunds-pg-dump
          path: futurefunds-*.sql
        # Artifacts are retained 90 days. Good enough for v1.
```

Restore from a dump:
```bash
psql "$DATABASE_URL" < futurefunds-20260621T030000Z.sql
```

### 5.3 Schema-experiment workflow (free)

Neon branching makes "try the migration on a copy" trivial:

1. Neon console → branch from `main` → `experiment-add-tags`.
2. Copy the branch's pooled connection string to a
   `FF_DATABASE_URL_STAGING` secret.
3. From your laptop, point a local `uvicorn` at that branch.
4. `alembic upgrade head` — experiment freely.
5. Delete the branch when done; storage reverts.

For v1 this is manual. Render's **Pull Request Previews** (paid
feature, $7/mo) would automate it.

### 5.4 Observability

- **Logs:** Render captures stdout/stderr from the container and
  shows them in the dashboard with 7-day retention. The structured
  JSON logger from Phase 1 (C5) renders as a per-line JSON view;
  the `x-request-id` makes it easy to follow a single request.
- **Metrics:** Render exposes CPU%, memory%, request count, and
  HTTP status counts in the dashboard. The free tier is enough for
  a personal app.
- **No external monitoring (yet).** The 7-day log retention and
  `/readyz` endpoint are enough to debug issues; an UptimeRobot
  ping on `/readyz` (free, 5-min interval) gives a "service is up"
  signal that survives your laptop being closed.
- **No external log shipping.** If we later want Loki/Datadog,
  Render supports log drains (paid) or we can add a sidecar
  container that tails Render's log stream.

### 5.5 Cold starts on the free tier

Render spins down the web service after 15 minutes without traffic.
The next request pays a cold-start cost of ~30 seconds (image pull
+ container start + uvicorn boot). For a personal app this is
acceptable. Mitigations if it ever gets annoying:

- Upgrade to Render's $7/mo **Starter** plan → always on, no
  spin-down, faster cold starts.
- Add a free UptimeRobot ping every 14 minutes to keep the service
  warm (works, slightly silly).
- Accept it. The dashboard is fine to wait 30 s on first load each
  morning.

### 5.6 Memory budget (free tier is 512 MB)

The container imports `pandas`, `numpy`, and `statsmodels` at
startup. Their combined resident set is ~200–300 MB on the slim
base image, leaving ~200 MB headroom on the free tier. This is
fine for v1; if we add heavier workloads (large CSV imports, etc.)
we should:

- Move the heavy imports behind a function (lazy import) so the
  cold-start path is lighter, or
- Upgrade to a paid plan with more RAM.

---

## 6. Phase 5 — Post-launch hardening (optional, but cheap)

| Item | Effort |
|---|---|
| Pin all dependencies with `uv lock` or `pip-compile` | 0.5 h |
| Add `GZipMiddleware` for JSON API responses | 5 min |
| Add CSP, X-Frame-Options, Referrer-Policy headers in middleware | 15 min |
| Add `slowapi` rate limiting on form posts | 1 h |
| Migrate `/docs` and `/redoc` behind auth (they currently leak schema) | 5 min |
| Switch from `uvicorn` direct to `gunicorn -k uvicorn.workers.UvicornWorker` (only matters if we move off free) | 15 min |
| Add a GitHub Actions workflow: lint + test + build image on every push to `main` | 2 h |
| Lazy-import `pandas`/`statsmodels` to reduce free-tier cold start | 0.5 h |
| Configure Render **Pull Request Previews** (paid, $7/mo) for safe schema migrations | 0.5 h |
| Move recurring-rule materialization off API path to a scheduled Render Cron Job (paid) | 1 h |

Items removed from the previous (GCP) plan: **Migrate DB to
Postgres** (done as part of Phase 3), **multi-arch Docker
build for Artifact Registry** (Render builds the image itself, no
registry needed), **GCPLogs driver** (Render handles log capture
natively).

---

## 7. Implementation order (concrete checklist)

- [x] **Phase 1** (completed 2026-06-19 — see §2 for details)
  - [x] C1 — fix `Dockerfile` (multi-stage Node + Python build, non-root user, proxy headers)
  - [x] C2 — add `.dockerignore`
  - [x] C3 — fix `.env.example` (currency escape, debug=false) — SSO keys deferred to Phase 2
  - [x] C4 — compile Tailwind CSS, update `base.html`, multi-stage Docker build for CSS
  - [x] C5 — structured logging (JSON in prod, plain text in dev, request middleware, per-rule recurring logs)
  - [x] C6 — split `/healthz` / `/readyz` (DB probe + settings sanity check)
  - [x] Verify: `pytest` 203/203 passing; `ruff check app/ tests/` clean; both endpoints return 200; compiled CSS = 19.7 KB
- [x] **Phase 2** (completed — see README.md Phase 9)
  - [x] Add `authlib`, `itsdangerous` to `pyproject.toml`
  - [x] Add `User` model + migration
  - [x] Add `user_id` FK columns + scope all CRUD
  - [x] Add `auth.py` router + `login.html`
  - [x] Wire `SessionMiddleware` + `HTTPSRedirectMiddleware` + `TrustedHostMiddleware`
  - [x] Update `conftest.py` to create a default user
  - [x] Add `test_auth.py` (login flow, isolation)
  - [x] Add SSO / session keys to `.env.example`
  - [x] Verify: all tests passing
- [ ] **Phase 3** — code (small)
  - [ ] C7 — add `psycopg[binary]>=3.1.18` to `backend/requirements.txt`
  - [ ] C8 — update `backend/app/database.py` for `pool_pre_ping` + `pool_recycle` when not SQLite
  - [ ] C9 — update `.env.example` to show Postgres URL (keep commented SQLite for local)
  - [ ] C11 — change `Dockerfile` CMD to honor `${PORT:-8000}`
  - [ ] Verify: `pytest` still passes against a local Postgres (start a throwaway `neondb` branch or use `docker run postgres`)
- [ ] **Phase 3** — platform setup
  - [ ] Create Neon project, pick region, copy pooled `DATABASE_URL`
  - [ ] Add `render.yaml` at repo root
  - [ ] Push `render.yaml` and code to `main`
  - [ ] Render dashboard → **New → Blueprint** → connect repo → create service
  - [ ] Set secret env vars in Render: `FF_DATABASE_URL`, `FF_GOOGLE_CLIENT_ID`, `FF_GOOGLE_CLIENT_SECRET`
  - [ ] Confirm `releaseCommand` ran (`alembic upgrade head` succeeded) and `/healthz` returns 200
  - [ ] Update Google OAuth **Authorized redirect URIs** to include `https://yourapp.onrender.com/auth/google/callback`
  - [ ] Visit `https://yourapp.onrender.com/login`, sign in, create an account, record a transaction
  - [ ] (Optional) Add custom domain, update `FF_ALLOWED_HOSTS` + OAuth redirect URI
- [ ] **Phase 4** — backups + monitoring
  - [ ] Verify Neon PITR: create a branch from "1 hour ago" via console, confirm data is intact
  - [ ] Add `.github/workflows/pg-backup.yml`, store `NEON_DATABASE_URL` as a repo secret
  - [ ] Run the workflow manually once, download the artifact, sanity-check the dump
  - [ ] (Optional) Add UptimeRobot ping on `/readyz`
  - [ ] (Optional) Configure Render log drain to a real log sink (deferred)

---

## 8. Security risk matrix (post-deploy, with all phases complete)

| Risk | Mitigation |
|---|---|
| Public access to financial data | Google SSO required for any request |
| Cross-user data leak | All queries scoped by `user_id` + isolation tests |
| DDoS | Render's edge absorbs volumetric attacks; HTTP-level WAF is not included on the free tier (acceptable for personal app) |
| TLS MITM | Render-issued Let's Encrypt cert for `*.onrender.com` and any custom domain. HTTP→HTTPS redirect via `HTTPSRedirectMiddleware`. |
| Origin IP exposure | The app runs on Render's shared infrastructure; the "origin IP" is the Render service's internal address, not a discoverable VM. No attack surface beyond what Render itself exposes. |
| App-server compromise | Render sandboxes containers; the attack surface is the Python app + its deps. No `cloudflared` credential, no SSH access, no persistent disk to exfiltrate. |
| DB loss | Neon PITR (7-day free tier) + weekly GitHub Actions `pg_dump` to Artifacts (90-day retention). |
| Secret leak | `.env` not committed (`.gitignore`), not in Docker image (`.dockerignore`), set as Render secret env vars (encrypted at rest, masked in UI). |
| Credential stuffing on `/auth/login` | Google OAuth — no password to stuff. Render free tier doesn't ship WAF rate-limiting, but the OAuth redirect makes blind POSTs useless. |
| CSRF on form posts | SameSite=Lax session cookies + Google SSO requires interactive login. |
| SQL injection | SQLAlchemy ORM + parameterized queries throughout. (Now on Postgres, so no SQLite `text(...)` footguns.) |
| Dependency supply-chain attack | Pinned versions via `uv.lock` (Phase 5). |
| Runaway API cost | Render free tier has hard limits (750 hr/mo, 512 MB RAM); Neon free tier has 191.9 compute hours and 0.5 GB storage. Both will simply refuse to scale past the cap rather than charging. |
| Cold-start timeout | `/healthz` is fast (no DB hit) so Render's rollout doesn't time out; 30 s cold start is a UX issue, not a security one. |
| Postgres connection storm on cold start | `pool_pre_ping=True` + pooled endpoint keep connection count bounded. |

---

## 9. Open items deferred to v2

- Multi-user shared budgets (a budget shared between two Google accounts).
- Per-user data export (CSV / JSON).
- Webhooks for recurring rule events.
- Mobile app (current mobile UX is responsive but not native).
- Auth providers beyond Google (Microsoft, Apple, etc.).
- Per-account currency + FX conversion.
- Receipt attachments (will need Render Persistent Disk or S3).
- Two-factor auth (TOTP) — Google SSO already provides strong auth, but if you ever add password auth, TOTP becomes important.
- Move off Render free tier when traffic warrants (Starter $7/mo gets always-on, no spin-down, and PR previews).
- Move off Neon free tier when storage > 0.5 GB or compute > 191.9 hr/mo (Launch $19/mo gets 30-day PITR, larger compute, IP allowlists).
- Database connection pool tuning under high concurrency (e.g., pgbouncer in front of a direct Neon endpoint).
- Local CI that boots a real Postgres in Docker for the test suite to mirror prod.

Items removed from the previous (GCP) plan: **Postgres migration**
(done as part of Phase 3 — we're on Neon from day one).
