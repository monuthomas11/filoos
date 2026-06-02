"""CRUD helpers for the Account model."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import ACCOUNT_TYPE_COLORS, Account
from app.schemas.account import AccountCreate, AccountUpdate


def list_accounts(db: Session) -> list[Account]:
    return db.query(Account).order_by(Account.created_at).all()


def get_account(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def create_account(db: Session, data: AccountCreate) -> Account:
    payload = data.model_dump()
    # Infer a default colour from the account type if none was provided.
    if payload.get("color") is None:
        payload["color"] = ACCOUNT_TYPE_COLORS.get(data.type, "#4f46e5")
    account = Account(**payload)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_account(
    db: Session, account_id: int, data: AccountUpdate
) -> Account | None:
    account = get_account(db, account_id)
    if account is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account_id: int) -> bool:
    account = get_account(db, account_id)
    if account is None:
        return False
    db.delete(account)
    db.commit()
    return True


def compute_balance(account: Account, db: Session) -> Decimal:
    """Return the current balance by summing opening_balance + all transactions."""
    from app.crud.transaction import compute_account_balance

    return compute_account_balance(account, db)
