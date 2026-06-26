# Account Dashboard Display & Balance Control Implementation Plan

## Overview
Add two new flags to accounts for controlling dashboard display and balance inclusion, plus enforce credit card balance constraints.

## Requirements
1. **Show on Dashboard**: Flag to decide whether to display the account card on dashboard
2. **Include in Total**: Flag to decide whether to count the account's balance toward total balances
3. **Credit Card Balance**: Restrict credit card balances to be negative or zero (both opening_balance and computed balance)

## Current State
- Accounts have `is_active` flag but no control over dashboard display or balance inclusion
- Balance = `opening_balance` + sum of all transactions
- Credit cards use same model as other accounts (no special balance handling)
- Total balance sums ALL active accounts unconditionally

---

## Proposed Changes

### New Account Fields

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `show_on_dashboard` | bool | `true` | Whether to display the account card on dashboard |
| `include_in_total` | bool | `true` | Whether to count this account's balance toward total |

### Credit Card Constraints

| Constraint | Rule |
|------------|------|
| `opening_balance` | Must be <= 0 |
| Computed balance | Must be <= 0 (validated on save) |

---

## Files That Need Changes

### Database Layer
1. `backend/app/models/account.py` - Add new fields to Account model
2. `backend/app/schemas/account.py` - Add fields to Pydantic schemas
3. `backend/alembic/versions/` - New migration file

### Backend Logic
4. `backend/app/crud/account.py` - Update `list_accounts()` to filter by `show_on_dashboard`
5. `backend/app/crud/transaction.py` - Update `compute_total_balance()` to respect `include_in_total`

### Backend Validation
6. `backend/app/schemas/account.py` - Add validator for credit card balance <= 0

### Services
7. `backend/app/services/analytics.py` - Update `balance_trend()` to respect new flags
8. `backend/app/services/forecasting.py` - Update `balance_projection()` to respect new flags

### Frontend
9. `backend/app/templates/accounts/form.html` - Add checkboxes for new flags

---

## Implementation Steps

### Step 1: Update Account Model
**File:** `backend/app/models/account.py`

Add two new columns to the Account class:
```python
show_on_dashboard: Mapped[bool] = mapped_column(default=True)
include_in_total: Mapped[bool] = mapped_column(default=True)
```

### Step 2: Create Database Migration
**File:** `backend/alembic/versions/` (new file)

- Add `show_on_dashboard` column (default: true)
- Add `include_in_total` column (default: true)
- Update credit card `opening_balance` to 0 where > 0

### Step 3: Update Pydantic Schemas
**File:** `backend/app/schemas/account.py`

Add fields to:
- `AccountCreate`
- `AccountUpdate`
- `AccountResponse`

Add validator:
```python
@field_validator('opening_balance')
@classmethod
def validate_credit_card_balance(cls, v, info):
    # Will need context to check account type
    # Implementation details in code
```

### Step 4: Update CRUD Operations
**File:** `backend/app/crud/account.py`

Update `list_accounts()`:
```python
def list_accounts(
    db: Session, 
    active_only: bool = False, 
    user_id: int | None = None,
    show_on_dashboard: bool | None = None  # New parameter
) -> list[Account]:
```

**File:** `backend/app/crud/transaction.py`

Update `compute_total_balance()` to accept optional filter or filter internally based on account flags.

### Step 5: Update Services
**File:** `backend/app/services/analytics.py`

Update `balance_trend()` to filter accounts by `include_in_total`.

**File:** `backend/app/services/forecasting.py`

Update `balance_projection()` to filter accounts by `include_in_total`.

### Step 6: Update Frontend Form
**File:** `backend/app/templates/accounts/form.html`

Add two checkboxes:
- "Show on Dashboard" (checked by default)
- "Include in Total Balance" (checked by default)

---

## Key Design Decisions

1. **Default values**: Both flags default to `true` for backward compatibility
2. **Credit card validation**: Both opening_balance and computed balance must be <= 0
3. **Data migration**: Set credit card opening_balance to 0 if currently positive
4. **Independent flags**: An account can show on dashboard but not include in total (useful for tracking investments separately)

---

## Affected Components

| Component | File | Changes |
|-----------|------|---------|
| Dashboard Page | `app/routers/pages.py` | Uses `list_accounts()` - will automatically get new filter |
| Dashboard Template | `app/templates/dashboard.html` | No changes needed (uses accounts from query) |
| Account Card Partial | `app/templates/partials/account_card.html` | No changes needed |
| Dashboard API | `app/routers/dashboard.py` | Uses analytics service - will be updated |
| Account List | `app/templates/accounts/list.html` | No changes needed |

---

## Testing Checklist

- [ ] Create new account with both flags false - should not appear on dashboard
- [ ] Create new account with show_on_dashboard=true, include_in_total=false - appears on dashboard but not in total
- [ ] Create credit card with positive opening_balance - should show validation error
- [ ] Create credit card with negative opening_balance - should succeed
- [ ] Existing accounts retain behavior (both flags default to true)
- [ ] Dashboard total matches sum of accounts with include_in_total=true
- [ ] Analytics/forecasting services respect new flags
