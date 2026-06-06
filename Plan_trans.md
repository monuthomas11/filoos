# Plan — Quick-add Transaction (Redirect) + Modal (Future Enhancement)

> Standalone plan document for the "Quick-add transaction" feature. Contains full
> context for another agent to implement without needing to read PLAN.md.
> Project lives at `E:\Repos\future-funds`. Backend is FastAPI + SQLAlchemy + Jinja2.
> Frontend stack: HTMX 1.9, Alpine.js 3, Tailwind (Play CDN), Chart.js 4.

---

## 1. Background & Goal

The dashboard (`/`) currently has no way to add a transaction from itself. The
user must navigate to `/transactions/new` via the top nav, fill the form, submit,
and land on `/transactions`. This adds friction for the most common action in
the app.

**Goal**: Add a primary `+ Add transaction` button to the dashboard header that
links to the existing `/transactions/new` form. After a successful create, send
the user back to `/` (the dashboard) so they see refreshed data immediately.

**Modal variant is explicitly out of scope** for this plan. It is documented in
PLAN.md §12 as a future enhancement (and referenced at the bottom of this file
for context).

---

## 2. Decisions Already Made (with user)

| Question | Decision |
|---|---|
| UX approach | **Redirect** (option A). Modal is deferred to a future enhancement. |
| Cancel link on form | **Follows `next`** — if user came from dashboard, Cancel goes back to dashboard. |

---

## 3. Files to Change

### 3.1 `backend/app/templates/dashboard.html` (page header, lines 4–10)

Add a primary `+ Add transaction` button to the right of the page `<h1>`.

Current code (lines 3–10):

```html
{% block content %}
<section class="space-y-6">
  <div>
    <h1 class="text-2xl font-semibold tracking-tight">Dashboard</h1>
    <p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
      Welcome to {{ app_name }}.
    </p>
  </div>
```

Target: wrap the `<div>` (containing h1 + welcome) in a flex container with a
right-aligned link.

```html
{% block content %}
<section class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Dashboard</h1>
      <p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        Welcome to {{ app_name }}.
      </p>
    </div>
    <a
      href="/transactions/new?from=/"
      class="inline-flex items-center gap-1.5 rounded-lg bg-accent-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-accent-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
      Add transaction
    </a>
  </div>
```

The `?from=/` query param tells the form to send the user back to `/` after save.

### 3.2 `backend/app/routers/transactions.py`

#### Edit A — `transaction_create_page` (lines 150–168)

Add a `from_` query param and pass it to the template as `next_url`.

Current:

```python
@router.get("/transactions/new", response_class=HTMLResponse)
async def transaction_create_page(
    request: Request,
    db: Session = Depends(get_db),
):
    accounts = list_accounts(db)
    categories = list_categories(db)
    return templates.TemplateResponse(
        request,
        "transactions/form.html",
        {
            "title": "New Transaction",
            "mode": "create",
            "transaction": None,
            "accounts": accounts,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
        },
    )
```

Target:

```python
@router.get("/transactions/new", response_class=HTMLResponse)
async def transaction_create_page(
    request: Request,
    from_: str | None = Query(None, alias="from"),
    db: Session = Depends(get_db),
):
    accounts = list_accounts(db)
    categories = list_categories(db)
    return templates.TemplateResponse(
        request,
        "transactions/form.html",
        {
            "title": "New Transaction",
            "mode": "create",
            "transaction": None,
            "accounts": accounts,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
            "next_url": from_ if from_ and from_.startswith("/") else None,
        },
    )
```

#### Edit B — `transaction_create` POST (lines 218–291)

Add a `next` form field. If safe (starts with `/`, no `//`, no `:`), use it as the
HX-Redirect target; otherwise keep the current `/transactions` fallback.

Current signature (lines 218–231):

```python
@router.post("/transactions")
async def transaction_create(
    request: Request,
    type: str = Form(...),
    amount: Decimal = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    notes: str | None = Form(None),
    account_id: int | None = Form(None),
    category_id: int | None = Form(None),
    from_account_id: int | None = Form(None),
    to_account_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
```

Target:

```python
@router.post("/transactions")
async def transaction_create(
    request: Request,
    type: str = Form(...),
    amount: Decimal = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    notes: str | None = Form(None),
    account_id: int | None = Form(None),
    category_id: int | None = Form(None),
    from_account_id: int | None = Form(None),
    to_account_id: int | None = Form(None),
    next: str | None = Form(None),
    db: Session = Depends(get_db),
):
```

Then replace the HX-Redirect line at the bottom of the function (line 290):

```python
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/transactions"})
    return TransactionRead.model_validate(tx)
```

with:

```python
    if is_htmx(request):
        redirect_target = _safe_next(next) or "/transactions"
        return Response(status_code=200, headers={"HX-Redirect": redirect_target})
    return TransactionRead.model_validate(tx)
```

And add the helper near the top of the file (next to `_get_amount_sign` around
line 35):

```python
def _safe_next(value: str | None) -> str | None:
    """Validate a `next` redirect target. Allow only same-origin absolute paths."""
    if not value or not isinstance(value, str):
        return None
    if not value.startswith("/"):
        return None
    if value.startswith("//") or ":" in value.split("/", 2)[1]:
        return None
    return value
```

### 3.3 `backend/app/templates/transactions/form.html`

#### Edit A — Add hidden `next` input

Insert immediately inside the `<form>` (line 17–22), after the opening tag:

```html
  <form
    id="transaction-form"
    hx-{{ hx_method.lower() }}="{{ form_action }}"
    hx-on::before-request="return validateTransferForm()"
    class="mt-6 space-y-5"
  >
    <input type="hidden" name="next" value="{{ next_url or '/transactions' }}" />
```

#### Edit B — Make the Cancel link follow `next_url`

Current (line 143):

```html
      <a href="/transactions" class="text-sm text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300">Cancel</a>
```

Target:

```html
      <a href="{{ next_url or '/transactions' }}" class="text-sm text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300">Cancel</a>
```

### 3.4 `backend/tests/test_transactions.py`

Add the following 4 tests at the end of the file. The existing fixtures
(`client`, `db_session`) from `tests/conftest.py` are sufficient.

```python
# ------------------------------------------------------------------
# Quick-add redirect (Phase 4.1) — dashboard CTA + next-param threading
# ------------------------------------------------------------------


def test_dashboard_has_add_transaction_button(client: TestClient):
    """The dashboard must contain a primary CTA linking to /transactions/new."""
    r = client.get("/")
    assert r.status_code == 200
    assert "/transactions/new" in r.text
    assert "Add transaction" in r.text


def test_dashboard_button_passes_from_query_param(client: TestClient):
    """The dashboard CTA must include ?from=/ so the form knows the entry point."""
    r = client.get("/")
    assert r.status_code == 200
    # Find the link to the create form and verify it carries ?from=/
    assert 'href="/transactions/new?from=/"' in r.text


def test_create_form_renders_next_hidden_input(client: TestClient):
    """GET /transactions/new?from=/ must render a hidden next input set to '/'."""
    r = client.get("/transactions/new", params={"from": "/"})
    assert r.status_code == 200
    assert 'name="next" value="/"' in r.text


def test_create_form_default_next_is_transactions(client: TestClient):
    """GET /transactions/new (no from param) must default next to /transactions."""
    r = client.get("/transactions/new")
    assert r.status_code == 200
    assert 'name="next" value="/transactions"' in r.text


def test_create_via_htmx_with_next_returns_custom_redirect(client: TestClient, db_session: Session):
    """POST /transactions with next=/ and a valid payload must return HX-Redirect: /."""
    # Need at least one account for the form to be valid
    from app.crud.account import create_account
    from app.models.account import AccountType
    from decimal import Decimal

    acc = create_account(
        db=db_session,
        name="Test Account",
        type=AccountType.CASH,
        currency="INR",
        opening_balance=Decimal("0"),
    )
    db_session.commit()

    r = client.post(
        "/transactions",
        data={
            "type": "expense",
            "account_id": str(acc.id),
            "amount": "10.00",
            "description": "Coffee",
            "date": "2026-06-05",
            "next": "/",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers.get("HX-Redirect") == "/"


def test_create_via_htmx_without_next_falls_back_to_transactions(client: TestClient, db_session: Session):
    """POST /transactions with no next field must fall back to HX-Redirect: /transactions."""
    from app.crud.account import create_account
    from app.models.account import AccountType
    from decimal import Decimal

    acc = create_account(
        db=db_session,
        name="Test Account 2",
        type=AccountType.CASH,
        currency="INR",
        opening_balance=Decimal("0"),
    )
    db_session.commit()

    r = client.post(
        "/transactions",
        data={
            "type": "expense",
            "account_id": str(acc.id),
            "amount": "5.00",
            "description": "Tea",
            "date": "2026-06-05",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert r.headers.get("HX-Redirect") == "/transactions"


def test_create_via_htmx_rejects_unsafe_next(client: TestClient, db_session: Session):
    """POST /transactions with a non-local next value must fall back to /transactions."""
    from app.crud.account import create_account
    from app.models.account import AccountType
    from decimal import Decimal

    acc = create_account(
        db=db_session,
        name="Test Account 3",
        type=AccountType.CASH,
        currency="INR",
        opening_balance=Decimal("0"),
    )
    db_session.commit()

    for bad in ("//evil.com/x", "http://evil.com", "javascript:alert(1)"):
        r = client.post(
            "/transactions",
            data={
                "type": "expense",
                "account_id": str(acc.id),
                "amount": "1.00",
                "description": "X",
                "date": "2026-06-05",
                "next": bad,
            },
            headers={"HX-Request": "true"},
        )
        assert r.status_code == 200, f"Bad next={bad!r} returned {r.status_code}"
        assert r.headers.get("HX-Redirect") == "/transactions", (
            f"Bad next={bad!r} should fall back to /transactions"
        )


def test_cancel_link_follows_next(client: TestClient):
    """The Cancel link on the create form must point to next_url when provided."""
    r = client.get("/transactions/new", params={"from": "/"})
    assert r.status_code == 200
    # The Cancel link should be '/' when next is '/'
    assert 'href="/"' in r.text
```

That's 7 tests in total (4 pure render + 3 with DB). All 7 are required for full coverage. The 4 minimum from the agreed plan are the first 4; the last 3 cover the POST redirect behavior the plan also calls out.

### 3.5 `PLAN.md` updates (do these last, after tests pass)

Three blocks, in the indicated sections.

**§9 Phased Roadmap — insert after Phase 4 row:**

```
| 4.1 | **Quick-add (redirect)** | Primary `+ Add transaction` button on the dashboard linking to `/transactions/new`; form's `next` query param threaded through so a successful create redirects back to `/` if invoked from the dashboard | Click button on dashboard, submit form, land back on dashboard with refreshed data |
```

**§12 Future-Proofing — add a new bullet:**

```
- **Quick-add transaction modal on the dashboard** — currently the dashboard links to the full `/transactions/new` page. A future enhancement would add an Alpine.js modal that lazy-loads the form via `hx-get="/transactions/new?partial=1"`, submits in place, and refreshes dashboard widgets (KPIs, charts, account balances, recent transactions) via HTMX partial swaps. The form would be extracted into `partials/transaction_form.html` so the same partial is reused by the modal and the full create page.
```

**§14 Changelog — insert a new entry in chronological order (between Phase 4 and Phase 5):**

```
### Phase 4.1 — Quick-add transaction (redirect) (complete)

Shipped:
- `backend/app/templates/dashboard.html` — primary `+ Add transaction` button in the page header; links to `/transactions/new?from=/`.
- `backend/app/routers/transactions.py` — `GET /transactions/new` accepts optional `?from=<path>`; `POST /transactions` accepts a `next` form field and returns `HX-Redirect: <next>` for safe local paths (falls back to `/transactions` on missing/invalid input). New `_safe_next` helper enforces same-origin policy (rejects `//evil.com`, `http://...`, `javascript:`).
- `backend/app/templates/transactions/form.html` — hidden `next` input; "Cancel" link now respects `next_url`.
- `backend/tests/test_transactions.py` — 7 new tests (button presence, `?from=/` query param, hidden `next` input, default value, custom redirect, fallback redirect, open-redirect guard).

Verified:
- `pytest -q` → **141 passed** (134 + 7 new).
- Dashboard renders a primary CTA linking to `/transactions/new?from=/`.
- `GET /transactions/new?from=/` then POST → browser lands on `/` after save.
- Open-redirect attempts (`//evil.com`, `http://evil.com`, `javascript:alert(1)`) are rejected and fall back to `/transactions`.
- ruff clean.

Future enhancement (deferred): quick-add modal — see §12.
```

---

## 4. Verification Steps

```bash
# from E:\Repos\future-funds
scripts\dev.ps1     # or ./scripts/dev.sh
# browser: open http://127.0.0.1:8000
# 1. See "Add transaction" button in dashboard header
# 2. Click it -> form opens with date=today
# 3. Fill and submit -> lands on /, see new row in recent transactions, balance updated
# 4. Press Cancel on the form -> lands back on /
```

```bash
cd backend
pytest -q
# expect: 141 passed
```

```bash
cd backend
ruff check .
# expect: clean
```

---

## 5. Out of Scope (Documented in PLAN.md §12)

- **Quick-add modal**: Alpine.js modal with lazy-loaded form via
  `hx-get="/transactions/new?partial=1"`, in-place submit, and HTMX partial
  refresh of dashboard widgets. Form would be extracted into
  `partials/transaction_form.html` and reused by both the modal and the full
  create page. The current `transactions/form.html` already extends `base.html`
  so it cannot be embedded directly — partial extraction is a prerequisite for
  the modal.

---

## 6. Key Code References (for the implementing agent)

- Dashboard page handler: `backend/app/routers/pages.py:19-38`
- Dashboard template: `backend/app/templates/dashboard.html` (header at L4-10)
- Transaction form page handler: `backend/app/routers/transactions.py:150-168`
- Transaction form POST: `backend/app/routers/transactions.py:218-291`
- Form template: `backend/app/templates/transactions/form.html`
- `is_htmx` helper: `backend/app/utils.py:13-15`
- Existing HTMX redirect pattern: `transactions.py:289-290` and
  `transactions.py:344-345` (both use `HX-Redirect` header)
- Test fixtures: `backend/tests/conftest.py` (`client`, `db_session`)
- Existing test patterns: `backend/tests/test_transactions.py`
  (`test_create_expense_via_htmx` at line 255 is a good template)
- Open-redirect guard pattern: the same `_safe_next` helper used here would be
  reusable for future `next` params on other forms (e.g., login redirects).
