# Filoos Rebrand — Implementation Plan

> Companion to README.md / PLAN.md / STATUS.md / deployment.md.
> Execute top-to-bottom, in the order shown. Items per your earlier decisions:
>
> - Rename brand strings everywhere they appear in user-facing / doc / URL contexts.
> - Keep `FF_` env var prefix as-is (internal; not user-visible).
> - Keep `FF_COLORS` and `ff-dark` localStorage key as-is (internal token).
> - Use `filoos.onrender.com` for Render hostname (matches existing `name: filoos` in `render.yaml`).
> - Binary `logo.png` / `favicon.png` are out of scope; HTML references stay the same.

---

## Group 1 — Brand-visible code (Python)

| File | Line | Change |
|---|---|---|
| `backend/app/config.py` | 49 | `app_name` default: `"FutureFunds"` → `"Filoos"` |
| `backend/app/__init__.py` | 1 | Docstring → `"""Filoos - personal expense tracker."""` |
| `backend/app/main.py` | 34 | Log message: `"starting FutureFunds"` → `"starting Filoos"` |
| `backend/app/main.py` | 44 | Log message: `"FutureFunds shutting down"` → `"Filoos shutting down"` |
| `backend/app/templates/base.html` | 7 | `<meta name="description">` text: `FutureFunds - personal expense tracker` → `Filoos - personal expense tracker` |
| `backend/app/static/js/app.js` | 1 | Banner comment `// FutureFunds - small client-side helpers.` → `// Filoos - small client-side helpers.` |
| `backend/app/static/js/app.js` | 83 | `console.debug("FutureFunds frontend ready.")` → `console.debug("Filoos frontend ready.")` |
| `backend/app/static/css/app.css` | 5 | Banner comment `/* FutureFunds - small overrides + transitions.` → `/* Filoos - small overrides + transitions.` |
| `backend/alembic/env.py` | 3 | Docstring: `the FutureFunds app package` → `the Filoos app package` |
| `backend/alembic.ini` | 1 | Comment: `# Alembic configuration for FutureFunds.` → `# Alembic configuration for Filoos.` |
| `scripts/dev.ps1` | 1 | Header comment `# FutureFunds - dev launcher ...` → `# Filoos - dev launcher ...` |
| `scripts/dev.sh` | 2 | Header comment `# FutureFunds - dev launcher ...` → `# Filoos - dev launcher ...` |
| `scripts/seed.py` | 1 | Docstring: `"""Seed the FutureFunds database ...` → `"""Seed the Filoos database ...` |

## Group 2 — Package metadata

| File | Line | Change |
|---|---|---|
| `backend/pyproject.toml` | 2 | `name = "futurefunds"` → `name = "filoos"` |
| `backend/pyproject.toml` | 4 | `description = "FutureFunds - a personal expense tracker..."` → `description = "Filoos - a personal expense tracker with a lightweight dashboard and balance predictions."` |
| `backend/pyproject.toml` | 7 | `authors = [{ name = "FutureFunds" }]` → `authors = [{ name = "Filoos" }]` |
| `backend/package.json` | 2 | `"name": "futurefunds-frontend"` → `"name": "filoos-frontend"` |
| `backend/package.json` | 4 | `"description": "FutureFunds frontend build (Tailwind CSS)."` → `"description": "Filoos frontend build (Tailwind CSS)."` |
| `backend/package-lock.json` | 2 | `"name": "futurefunds-frontend"` → `"name": "filoos-frontend"` |
| `backend/package-lock.json` | 7 | `"name": "futurefunds-frontend"` → `"name": "filoos-frontend"` |

## Group 3 — Tests

| File | Line | Change |
|---|---|---|
| `backend/tests/test_config.py` | 17 | `assert settings.app_name == "FutureFunds"` → `assert settings.app_name == "Filoos"` |
| `backend/tests/test_smoke.py` | 20 | `assert "FutureFunds" in body` → `assert "Filoos" in body` |
| `backend/tests/test_smoke.py` | 55 | `allowed_hosts=["futurefunds.onrender.com"]` → `allowed_hosts=["filoos.onrender.com"]` (and update the inline comment to match) |
| `backend/tests/test_smoke.py` | 62 | `base_url="https://futurefunds.onrender.com"` → `base_url="https://filoos.onrender.com"` |
| `backend/tests/ui_simulation.py` | 20 | `assert "FutureFunds" in r.text` → `assert "Filoos" in r.text` |

## Group 4 — Environment template

| File | Line | Change |
|---|---|---|
| `.env.example` | 1 | Header comment: `# FutureFunds environment configuration` → `# Filoos environment configuration` |
| `.env.example` | 14 | `FF_APP_NAME=FutureFunds` → `FF_APP_NAME=Filoos` |

(`FF_` prefix lines 4, 8, 10 stay as-is — internal prefix unchanged.)

## Group 5 — Deployment artifacts

### `render.yaml`

| Line | Change |
|---|---|
| 36 | Comment: `(\`name: futurefunds\`)` → `(\`name: filoos\`)` |
| 37 | Comment: `\`futurefunds.onrender.com\`` → `\`filoos.onrender.com\`` |
| 38 | Comment: `\`futurefunds.onrender.com,app.example.com\`` → `\`filoos.onrender.com,app.example.com\`` |
| 41 | `value: "futurefunds.onrender.com"` → `value: "filoos.onrender.com"` |
| 50 | `value: "https://futurefunds.onrender.com/auth/google/callback"` → `value: "https://filoos.onrender.com/auth/google/callback"` |

(Line 3 already says `name: filoos` — leave as-is.)

### `deployment.md`

| Line | Change |
|---|---|
| 1 | `# FutureFunds v1 — Deployment Plan` → `# Filoos v1 — Deployment Plan` |
| 3 | Maintainer audience line: `deploying FutureFunds to a public URL` → `deploying Filoos to a public URL` |
| 181 | Code block: `FF_APP_NAME=FutureFunds` → `FF_APP_NAME=Filoos` |
| 281 | Prose: `/healthz → 200 {"status":"ok","app":"FutureFunds"}` → `"app":"Filoos"` |
| 616 | Code block: `name: futurefunds` → `name: filoos` |
| 691 | Prose: `the \`futurefunds\` web service` → `the \`filoos\` web service` |
| 705 | Prose: `Visit \`https://futurefunds.onrender.com/login\`` → `Visit \`https://filoos.onrender.com/login\`` |
| 740 | Prose: `So a service named \`futurefunds\` lives at` → `So a service named \`filoos\` lives at` |
| 741 | Prose: `\`https://futurefunds.onrender.com\`` → `\`https://filoos.onrender.com\`` |
| 742 | Prose: `contain \`futurefunds.onrender.com\`` → `contain \`filoos.onrender.com\`` |
| 744 | Prose: `\`futurefunds.onrender.com,app.example.com\`` → `\`filoos.onrender.com,app.example.com\`` |
| 847 | `--file="futurefunds-${ts}.sql"` → `--file="filoos-${ts}.sql"` |
| 851 | `name: futurefunds-pg-dump` → `name: filoos-pg-dump` |
| 852 | `path: futurefunds-*.sql` → `path: filoos-*.sql` |
| 858 | `psql "$DATABASE_URL" < futurefunds-20260621T030000Z.sql` → `psql "$DATABASE_URL" < filoos-20260621T030000Z.sql` |

## Group 6 — Docs

| File | Line | Change |
|---|---|---|
| `README.md` | 1 | `# FutureFunds` → `# Filoos` |
| `README.md` | 115 | Endpoint table: `{"status":"ok","app":"FutureFunds"}` → `"app":"Filoos"` |
| `README.md` | 130 | ASCII tree: `FutureFunds/` → `Filoos/` |
| `README.md` | 171 | Prose: `FutureFunds ships as a single FastAPI process ...` → `Filoos ships as a single FastAPI process ...` |
| `README.md` | 176 | `docker build -t futurefunds .` → `docker build -t filoos .` |
| `README.md` | 177 | `docker run -p 8000:8000 -v "$(pwd)/data:/app/data" futurefunds` → `... filoos` |
| `PLAN.md` | 1 | `# FutureFunds - Living Plan & Design Document` → `# Filoos - Living Plan & Design Document` |
| `PLAN.md` | 3 | `This document is the source of truth for FutureFunds architecture, design, and roadmap.` → `... for Filoos architecture, design, and roadmap.` |
| `PLAN.md` | 9 | `**FutureFunds** is a personal expense tracker ...` → `**Filoos** is a personal expense tracker ...` |
| `PLAN.md` | 64 | ASCII tree: `FutureFunds/` → `Filoos/` |
| `PLAN.md` | 449 | `GET /healthz returns {"status":"ok","app":"FutureFunds"}` → `"app":"Filoos"` |
| `PLAN.md` | 579 | Same `/healthz` reference as line 449 |
| `STATUS.md` | 1 | `# FutureFunds — Project Status (handoff snapshot)` → `# Filoos — Project Status (handoff snapshot)` |
| `STATUS.md` | 13 | Identity table: `FutureFunds (personal expense tracker)` → `Filoos (personal expense tracker)` |
| `STATUS.md` | 14 | Repo-root path: `E:\Repos\future-funds\` → `D:\Source code\filoos\` (matches current working dir; adjust if you prefer `E:\Repos\filoos\`) |
| `STATUS.md` | 72 | Smoke-test description: `returns 200 with correct JSON, GET / returns 200 containing "FutureFunds" and "Dashboard"` → `containing "Filoos"` |
| `STATUS.md` | 407 | `/healthz example: {"status":"ok","app":"FutureFunds"}` → `"app":"Filoos"` |
| `REVIEW_CHANGES.md` | 1 | `# UI Test Review — FutureFunds Phase 8` → `# UI Test Review — Filoos Phase 8` |
| `Plan_reporting.md` | 1 | `# FutureFunds — Reporting Module Implementation Plan` → `# Filoos — Reporting Module Implementation Plan` |
| `Plan_trans.md` | 5 | `Project lives at E:\Repos\future-funds.` → `Project lives at D:\Source code\filoos.` |

---

## Items NOT changing (per your earlier decisions)

- `FF_` env var prefix throughout (`FF_APP_NAME`, `FF_DATABASE_URL`, `FF_GOOGLE_CLIENT_ID`, etc.) — internal convention.
- `window.FF_COLORS` JS global and its 4 references in `dashboard.html`.
- `ff-dark` `localStorage` key in `base.html`.
- `backend/app/static/img/logo.png` and `favicon.png` (binary).
- HTML asset paths (`/static/img/logo.png`, `/static/img/favicon.png`).

---

## Post-edit manual steps (REQUIRED)

After all in-place edits land:

```powershell
# 1. Remove the old Python egg-info (it carries the old distribution name)
Remove-Item -LiteralPath "D:\Source code\future-funds\backend\futurefunds.egg-info" -Recurse -Force

# 2. Regenerate Python egg-info under the new name
cd "D:\Source code\future-funds\backend"
pip install -e ".[dev]"
# OR run the dev launcher, which does the same: ..\scripts\dev.ps1

# 3. (Optional) regenerate package-lock.json so it matches package.json
#    Skip this if you already hand-edited package-lock.json identically (Group 2 step 7).
npm install
```

`package-lock.json` MUST stay consistent with `package.json` — the Dockerfile runs `npm ci` (which fails on mismatch). Since you approved hand-editing `package-lock.json:2,7` to `"filoos-frontend"`, no further regeneration is needed; `npm ci` will succeed.

---

## Verification

```powershell
cd "D:\Source code\future-funds\backend"
pytest -q                  # all tests pass
ruff check .               # clean

# Spot-check regenerated artifacts:
Get-ChildItem filoos.egg-info   # exists with new name
Get-Content filoos.egg-info\PKG-INFO | Select-Object -First 5
# Expected:
#   Metadata-Version: 2.4
#   Name: filoos
#   Summary: Filoos - a personal expense tracker ...
```

Spot-check `/healthz` returns the new app name:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/healthz
# Expected: {"status":"ok","app":"Filoos"}
```

Final audit grep (should return zero hits after egg-info regeneration):

```powershell
rg -i 'futurefunds|future-funds|future_funds' `
   --glob '!node_modules' `
   --glob '!.venv' `
   --glob '!*.pyc'
```

---

## Summary

- ~36 files touched (all in-place text edits; no moves, no renames).
- 2 manual post-steps: delete old egg-info, run `pip install -e ".[dev]"` to regenerate under the new name. `npm install` is optional (skipped if you hand-edit `package-lock.json` exactly).
- No git/remote changes (out of scope; flag for follow-up).
- No file-system directory renames (out of scope; flag for follow-up).

## Follow-ups (out of scope here — flagging for your awareness)

1. Rename local repo directory `D:\Source code\future-funds` → `D:\Source code\filoos`. Close all IDEs/shells first.
2. Rename GitHub remote if `origin` points at a `future-funds` repo.
3. Replace `logo.png` / `favicon.png` with Filoos-branded art (HTML paths are unchanged so it's a one-file swap).
4. If you ever set a custom domain, update `FF_ALLOWED_HOSTS` + `FF_GOOGLE_REDIRECT_URI` (one-line change in `render.yaml`).
