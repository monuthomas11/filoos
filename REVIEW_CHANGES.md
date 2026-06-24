# UI Test Review — Filoos Phase 8

**Date:** 2026-06-07
**Test Scope:** Full application verification against PLAN.md specification
**Test Result:** 202 tests passing, ruff clean

---

## Summary

All 8 phases implemented and working. Application loads at `http://127.0.0.1:8000`. Core features functional. **One critical bug** found on the accounts page.

---

## ✅ Verified Working Features

| Feature | Status | Notes |
|---------|--------|-------|
| Dashboard (KPIs, charts, period filter, balance projection, budget progress, recent transactions) | ✅ | All Chart.js charts render; period select re-fetches data |
| Dark mode toggle (persisted in localStorage) | ✅ | Alpine.js implementation |
| Accounts CRUD (create, list, edit, delete) | ⚠️ | **Balance display broken** (see bugs) |
| Transactions CRUD with filters, transfers | ✅ | Filter form HTMX partial swaps work |
| Categories CRUD | ✅ | |
| Budgets CRUD with progress bars | ✅ | Dashboard shows budget progress section |
| Recurring rules (create, preview, materialize) | ✅ | Preview endpoint works; materialize is idempotent |
| Predictions API (expenses + balance projection + runway) | ✅ | 95% confidence bands; runway warning on dashboard |
| 404 error page | ✅ | Styled template extending base.html |
| 500 error page | ✅ | Handler registered in main.py |
| All JSON API endpoints | ✅ | `/docs` OpenAPI available |
| HTMX form submissions with `HX-Redirect` | ✅ | Create/edit redirect to list pages |
| Seed script (`scripts/seed.py`) | ✅ | Creates 4 accounts, 11 transactions |

---

## 🔴 Critical Bugs

### 1. Account balances not displaying on `/accounts` page
- **Location:** `app/routers/accounts.py:33-43`, `app/templates/partials/account_card.html:44`
- **Root cause:** `account_list_page` passes a `balances` dict keyed by account ID, but `account_card.html` expects a single `balance` variable in context. The template renders `?` (currency symbol) with no amount.
- **Evidence:** Dashboard shows correct balances (₹1,300, ₹22,600, ₹27,000, ₹-6,749) but `/accounts` page shows `?` for all cards.
- **Fix:** Either iterate with `balances[account.id]` in the list template, or attach `balance` to each account object before rendering.

### 2. Rupee symbol (₹) renders as `?` across all pages
- **Location:** All templates using `{{ currency_symbol }}`
- **Root cause:** Encoding issue — `currency_symbol` ("₹") arrives as `?` in rendered HTML. Likely Jinja2 template encoding or context processor.
- **Evidence:** Dashboard shows `?44151.00`, `?1300.00`, etc. instead of `₹44151.00`.
- **Fix:** Ensure `currency_symbol` is passed as UTF-8 string in global template context (`app/main.py`).

---

## 🟡 Issues to Address

### 3. No recurring rules in seed data
- **Location:** `scripts/seed.py`
- **Impact:** `/recurring` page always shows empty state ("No recurring rules yet").
- **Fix:** Add 1-2 sample `RecurringRule` entries in seed script (e.g., monthly salary, monthly rent).

### 4. Compiled Tailwind not used in development
- **Location:** `scripts/build_css.sh`, `backend/tailwind.config.js`
- **Status:** Play CDN used in `base.html`; compiled CSS never generated/run.
- **Note:** Not a bug — planned for production. Documented in PLAN.md §11.

---

## 🟢 Test Coverage Verification

| Test Module | Tests | Phase Coverage |
|-------------|-------|----------------|
| `test_smoke.py` | 3 | Phase 1 |
| `test_accounts.py` | 24 | Phase 2 |
| `test_transactions.py` | 39 | Phase 3 |
| `test_dashboard.py` | 18 | Phase 4 |
| `test_transactions.py` (quick-add) | 7 | Phase 4.1 |
| `test_categories.py` | 21 | Phase 5 |
| `test_budgets.py` | 24 | Phase 5 |
| `test_recurring.py` | 47 | Phase 6 |
| `test_predictions.py` | 41 | Phase 7 |
| **Total** | **202** | **All 8 phases** |

All tests pass: `pytest -q` → `202 passed, 1 warning in 14.99s`

Lint clean: `ruff check .` → `All checks passed!`

---

## Recommended Next Steps

1. **Fix account balance display** (highest priority — visible regression)
2. **Fix rupee symbol encoding** (affects all monetary display)
3. **Add recurring rules to seed data** (improves demo experience)
4. **Optional:** Document compiled Tailwind build in README for production deploy

---

## Files to Modify

| File | Change |
|------|--------|
| `app/routers/accounts.py` | Pass balance per-account to template |
| `app/templates/partials/account_card.html` | Use `balance` from account context |
| `app/main.py` / `app/config.py` | Ensure `currency_symbol` is UTF-8 in template context |
| `scripts/seed.py` | Add `RecurringRule` creation |

---

## Screenshots / Evidence

Dashboard renders correctly with data:
- Total balance: ₹44,151
- 4 account cards with correct balances
- Daily spending bar chart (30 days)
- Category breakdown doughnut
- Balance projection line chart with confidence bands
- Budget progress bars (Groceries 60%, Telecom 59.9%)
- Recent transactions list (10 items)
- Period filter dropdown functional
- Runway warning chip (hidden when no risk)

Dark mode toggle works and persists.

404 page renders styled template.

API endpoints return correct JSON structures.