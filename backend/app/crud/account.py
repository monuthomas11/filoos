"""CRUD helpers for the Account model."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import ACCOUNT_TYPE_COLORS, Account, AccountType
from app.schemas.account import AccountCreate, AccountUpdate


def list_accounts(
    db: Session,
    active_only: bool = False,
    user_id: int | None = None,
    show_on_dashboard: bool | None = None,
    include_in_total: bool | None = None,
) -> list[Account]:
    q = db.query(Account)
    if user_id is not None:
        q = q.filter(Account.user_id == user_id)
    if active_only:
        q = q.filter(Account.is_active.is_(True))
    if show_on_dashboard is not None:
        q = q.filter(Account.show_on_dashboard.is_(show_on_dashboard))
    if include_in_total is not None:
        q = q.filter(Account.include_in_total.is_(include_in_total))
    return q.order_by(Account.created_at).all()


def get_account(db: Session, account_id: int, user_id: int | None = None) -> Account | None:
    q = db.query(Account).filter(Account.id == account_id)
    if user_id is not None:
        q = q.filter(Account.user_id == user_id)
    return q.first()


def create_account(db: Session, data: AccountCreate, user_id: int | None = None) -> Account:
    payload = data.model_dump()
    if payload.get("color") is None:
        payload["color"] = ACCOUNT_TYPE_COLORS.get(data.type, "#4f46e5")
    if user_id is not None:
        payload["user_id"] = user_id
    account = Account(**payload)
    db.add(account)
    db.flush()

    if data.type == AccountType.CREDIT_CARD:
        computed = compute_balance(account, db)
        if computed > 0:
            db.rollback()
            raise ValueError("Credit card computed balance must be zero or negative — reduce opening balance or clear transactions")

    db.commit()
    db.refresh(account)
    return account


def update_account(
    db: Session, account_id: int, data: AccountUpdate, user_id: int | None = None
) -> Account | None:
    account = get_account(db, account_id, user_id=user_id)
    if account is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.flush()

    if account.type == AccountType.CREDIT_CARD:
        computed = compute_balance(account, db)
        if computed > 0:
            db.rollback()
            raise ValueError("Credit card computed balance must be zero or negative — reduce opening balance or clear transactions")

    db.commit()
    db.refresh(account)
    return account


def has_transactions(db: Session, account_id: int) -> bool:
    """Return True if the account has any transactions."""
    from app.crud.transaction import count_transactions_for_account

    return count_transactions_for_account(db, account_id) > 0


def delete_account(
    db: Session, account_id: int, user_id: int | None = None
) -> tuple[bool, str | None]:
    """Delete an account. Returns (success, error_message).

    Blocks deletion if the account has transactions.
    """
    account = get_account(db, account_id, user_id=user_id)
    if account is None:
        return False, "Account not found"
    if has_transactions(db, account_id):
        return False, "Cannot delete account with existing transactions"
    db.delete(account)
    db.commit()
    return True, None


def compute_balance(account: Account, db: Session) -> Decimal:
    """Return the current balance by summing opening_balance + all transactions."""
    from app.crud.transaction import compute_account_balance

    return compute_account_balance(account, db)
