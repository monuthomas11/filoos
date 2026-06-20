# FutureFunds v1 — Deployment Plan

> **Audience:** the maintainer, deploying FutureFunds to a public URL on
> Google Cloud's free tier, fronted by Cloudflare. Companion to `README.md`,
> `PLAN.md`, and `STATUS.md`.
>
> **Status (2026-06-20):** Phase 1 (C1–C6) and Phase 2 (Google SSO +
> per-user data isolation) are ✅ complete — see §2 for what landed
> and §7 for the checklist. **Next up: Phase 3 (GCP + Cloudflare
> deployment).**

---

## 0. TL;DR

- **Host:** Google Cloud `e2-micro` Compute Engine VM (Always Free tier).
- **OS:** Debian 12, Docker runtime.
- **App:** single FastAPI container, SQLite database on a 30 GB standard
  persistent disk (`/app/data/expenses.db`).
- **Network:** Cloudflare Tunnel — the VM has **no public IP at all**.
  Cloudflare terminates TLS, then proxies through an outbound tunnel.
- **DNS + SSL:** Cloudflare Free tier — `Full (Strict)` SSL mode with a
  Cloudflare Origin Certificate on the origin.
- **Auth:** Google SSO via OAuth 2.0 — any Google account may sign in,
  but every user sees only their own data (`user_id` FK on every table).
- **Backups:** nightly in-disk snapshot of the SQLite file + monthly
  `gcloud compute snapshots create` of the persistent disk.
- **Estimated work:** ~2.25 days of focused effort across four phases.

---

## 1. Why this stack

| Choice | Reason |
|---|---|
| Compute Engine `e2-micro` | Only GCP Always Free compute target. 30 GB persistent disk included. SQLite-friendly. |
| Docker (not bare-metal Python) | One-command redeploy; mirrors `Dockerfile` already in repo; easy rollback via image tags. |
| SQLite | Schema is small, traffic is single-user, no migration needed for v1. `database_url` stays configurable so a Postgres migration is a one-line change later. |
| Persistent disk (not Cloud Storage FUSE) | Always Free, predictable latency, supports `fsync` (SQLite needs this for durability). |
| Cloudflare Tunnel | VM has no public IP → no public attack surface. Cloudflare provides DDoS protection + free SSL. Tunnel is `cloudflared` running on the VM. |
| Cloudflare DNS + `Full (Strict)` SSL | End-to-end HTTPS. Free Origin Certificate generated once in the dashboard. |
| Google SSO via `authlib` | Native OAuth 2.0 in FastAPI; user is already in the Google ecosystem. |
| Multi-user data isolation | `user_id` FK on every domain table, scoped queries everywhere. Cheap insurance against accidental cross-user data leak. |

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
  X-Forwarded-* headers that Cloudflare sets via the tunnel to be honored
  (otherwise HTTPS detection from `request.url.scheme` is wrong).
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

Current state:
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
   - `JsonFormatter` for production — one-line JSON per record with `time`/`level`/`logger`/`msg` and any `extra={}` fields. Parseable by Cloud Logging, `journalctl`, and Loki out of the box.
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

Logs go to **stdout only** (no file handler). Captured via `docker logs`, `journalctl`, or Cloud Logging.

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

## 3. Phase 2 — Google SSO + multi-user data isolation

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

## 4. Phase 3 — GCP + Cloudflare deployment

### 4.1 One-time GCP setup

```bash
# 1. Pick a free-tier region (us-west1, us-central1, us-east1).
export REGION=us-central1
export ZONE=us-central1-a
export PROJECT=your-gcp-project-id

gcloud config set project $PROJECT

# 2. Create a 30 GB persistent disk (free forever on e2-micro).
gcloud compute disks create futurefunds-data \
  --zone=$ZONE --size=30GB --type=pd-standard

# 3. Create the VM with NO public IP.
gcloud compute instances create futurefunds-vm \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --image-family=debian-12 --image-project=debian-cloud \
  --disk=auto-delete=no,boot=yes,device-name=boot \
  --disk=name=futurefunds-data,device-name=data-disk,mode=rw,boot=no \
  --no-address \
  --scopes=cloud-platform \
  --tags=cloudflared

# 4. Open IAP SSH (no public IP needed for SSH either).
gcloud compute ssh futurefunds-vm --zone=$ZONE
```

### 4.2 On the VM

```bash
sudo apt update && sudo apt install -y docker.io sqlite3

# Mount the persistent disk at /app/data (UUID-based so it's stable).
UUID=$(sudo blkid -s UUID -o value /dev/disk/by-id/google-data-disk)
echo "UUID=$UUID /app/data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
sudo mkdir -p /app/data && sudo mount -a
sudo chown -R $USER:$USER /app/data
chmod 700 /app/data

# Pull and run the container.
docker pull your-registry/futurefunds:1.0.0
docker run -d --name futurefunds \
  --restart unless-stopped \
  -v /app/data:/app/data \
  -e FF_DATABASE_URL=sqlite:////app/data/expenses.db \
  -e FF_SESSION_SECRET="$(openssl rand -base64 64)" \
  -e FF_GOOGLE_CLIENT_ID="..." \
  -e FF_GOOGLE_CLIENT_SECRET="..." \
  -e FF_GOOGLE_REDIRECT_URI="https://yourdomain.com/auth/google/callback" \
  -p 127.0.0.1:8000:8000 \
  your-registry/futurefunds:1.0.0
```

### 4.3 Cloudflare Tunnel

```bash
# Install cloudflared.
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
  | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# Login (opens browser, copy-paste the cert URL back).
cloudflared tunnel login

# Create the tunnel.
cloudflared tunnel create futurefunds

# Configure: /etc/cloudflared/config.yml
cat | sudo tee /etc/cloudflared/config.yml <<'YAML'
tunnel: futurefunds
credentials-file: /etc/cloudflared/<tunnel-id>.json

ingress:
  - hostname: yourdomain.com
    service: http://127.0.0.1:8000
  - service: http_status:404
YAML

# Route DNS via Cloudflare.
cloudflared tunnel route dns futurefunds yourdomain.com

# Run as a system service.
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

### 4.4 Cloudflare dashboard

| Step | Action |
|---|---|
| DNS | Confirm `yourdomain.com` has a `CNAME` to `<tunnel-id>.cfargotunnel.com` (the `tunnel route dns` command added this). |
| SSL/TLS | Set encryption mode to **Full (Strict)**. |
| Origin certificate | Dashboard → SSL → Origin Server → Create Certificate → save as `cert.pem` + `key.pem` on the VM (used only if you ever switch off the tunnel). With `cloudflared` you don't need to mount it — Cloudflare authenticates the tunnel itself. |
| WAF rules | (Free tier) Add rate-limit rule: 100 requests / 10 seconds per IP on `/auth/*`. |
| Caching | Bypass cache for `/api/*`, `/auth/*`, `*.db`. Cache static assets (`/static/*`) aggressively. |
| Security → Settings | Browser Integrity Check on; Challenge Passage: 30 minutes; Security Level: Medium. |

### 4.5 Firewall sanity check

Even though the VM has no public IP, verify nothing is listening on the
external interface:

```bash
sudo ss -tlnp   # only 127.0.0.1:8000 should appear
sudo iptables -L INPUT -n   # default policy ACCEPT is fine since no public IP
```

---

## 5. Phase 4 — Backups + monitoring

### 5.1 Nightly in-disk backup

```bash
# /etc/cron.daily/futurefunds-backup
#!/bin/bash
set -euo pipefail
DEST=/app/data/backups
mkdir -p "$DEST"
sqlite3 /app/data/expenses.db ".backup '$DEST/expenses-$(date -u +%F).db'"
# Keep last 30 days.
find "$DEST" -type f -mtime +30 -delete
```

Make it executable and verify the cron service is running.

### 5.2 Monthly disk snapshot

```bash
# /etc/cron.monthly/futurefunds-snapshot
#!/bin/bash
set -euo pipefail
gcloud compute disks snapshot futurefunds-data \
  --zone=us-central1-a \
  --snapshot-names=futurefunds-data-$(date -u +%F) \
  --description="Monthly FutureFunds snapshot"
# Retain last 6 snapshots.
gcloud compute snapshots list --filter="name~futurefunds-data-" \
  --sort-by=creationTimestamp --format="value(name)" \
  | head -n -6 \
  | xargs -r -n1 gcloud compute snapshots delete --quiet
```

### 5.3 Restore procedure

```bash
# On the VM, stop the container.
docker stop futurefunds

# From a local snapshot:
cp /app/data/backups/expenses-YYYY-MM-DD.db /app/data/expenses.db

# From a GCP snapshot:
gcloud compute disks create futurefunds-data-restore \
  --source-snapshot=futurefunds-data-YYYY-MM-DD \
  --zone=us-central1-a
# (then attach + mount in place)

docker start futurefunds
```

### 5.4 Observability

`uvicorn` access logs go to stdout — captured by `docker logs`. For
production, ship logs to Cloud Logging:

```bash
docker run -d --name futurefunds ... \
  --log-driver=gcplogs \
  your-registry/futurefunds:1.0.0
```

---

## 6. Phase 5 — Post-launch hardening (optional, but cheap)

| Item | Effort |
|---|---|
| Pin all dependencies with `uv lock` or `pip-compile` | 0.5 h |
| Add `GZipMiddleware` for JSON API responses | 5 min |
| Add CSP, X-Frame-Options, Referrer-Policy headers in middleware | 15 min |
| Add `slowapi` rate limiting on form posts | 1 h |
| Migrate `/docs` and `/redoc` behind auth (they currently leak schema) | 5 min |
| Switch from `uvicorn` direct to `gunicorn -k uvicorn.workers.UvicornWorker` | 15 min |
| Add a `Dockerfile` multi-arch build (`linux/amd64`) and push to Artifact Registry | 1 h |
| Add a GitHub Actions workflow: lint + test + build image on every push to `main` | 2 h |
| Migrate DB to Postgres + Cloud SQL when multi-user or Cloud Run is needed | 0.5-1 day |

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
- [ ] **Phase 3**
  - [ ] GCP: create disk + VM with `--no-address`
  - [ ] VM: mount disk, install Docker, run container
  - [ ] VM: install `cloudflared`, create tunnel, route DNS
  - [ ] Cloudflare dashboard: SSL = Full (Strict), WAF rule, cache rules
  - [ ] Verify: `https://yourdomain.com` returns the login page over HTTPS
- [ ] **Phase 4**
  - [ ] Add `/etc/cron.daily/futurefunds-backup`
  - [ ] Add `/etc/cron.monthly/futurefunds-snapshot`
  - [ ] Verify: `curl https://yourdomain.com/readyz` returns `{"status":"ok","database":"ok","settings":"ok"}`
  - [ ] Verify: backup file written, snapshot visible in `gcloud compute snapshots list`

---

## 8. Security risk matrix (post-deploy, with all phases complete)

| Risk | Mitigation |
|---|---|
| Public access to financial data | Google SSO required for any request |
| Cross-user data leak | All queries scoped by `user_id` + isolation tests |
| DDoS | Cloudflare edge protection (free tier) |
| TLS MITM | `Full (Strict)` SSL, HSTS preload-ready |
| Origin IP exposure | VM has no public IP; only `cloudflared` outbound tunnel |
| VM compromise | Only ingress = IAP SSH; no public ports; `cloudflared` is the only externally-reachable process |
| DB loss | Nightly in-disk backup (30-day retention) + monthly GCP snapshot (6-month retention) |
| Secret leak | `.env` not committed (`.gitignore`), not in Docker image (`.dockerignore`), injected at runtime |
| Credential stuffing on `/auth/login` | Cloudflare rate-limit + Google OAuth (no password to stuff) |
| CSRF on form posts | SameSite=Lax session cookies + Google SSO requires interactive login |
| SQL injection | SQLAlchemy ORM + parameterized queries throughout |
| Dependency supply-chain attack | Pinned versions via `uv.lock` (Phase 5) |
| Runaway API cost | `e2-micro` is free; Cloudflare free tier caps at 100k req/day on workers |

---

## 9. Open items deferred to v2

- Multi-user shared budgets (a budget shared between two Google accounts).
- Per-user data export (CSV / JSON).
- Webhooks for recurring rule events.
- Mobile app (current mobile UX is responsive but not native).
- Postgres migration (when SQLite becomes the bottleneck).
- Auth providers beyond Google (Microsoft, Apple, etc.).
- Per-account currency + FX conversion.
- Receipt attachments.
- Two-factor auth (TOTP) — Google SSO already provides strong auth, but if you ever add password auth, TOTP becomes important.
