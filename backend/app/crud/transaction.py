"""CRUD helpers for the Transaction model."""

from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction, TransactionType


def list_transactions(
    db: Session,
    account_id: int | None = None,
    type_filter: TransactionType | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    description: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[Transaction]:
    query = db.query(Transaction)
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    if type_filter is not None:
        query = query.filter(Transaction.type == type_filter)
    if date_from is not None:
        query = query.filter(Transaction.date >= date_from)
    if date_to is not None:
        query = query.filter(Transaction.date <= date_to)
    if description:
        query = query.filter(Transaction.description.ilike(f"%{description}%"))
    query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def get_transaction(db: Session, transaction_id: int) -> Transaction | None:
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def create_transaction(db: Session, account_id: int, amount: Decimal, type_: TransactionType,
                       description: str, date: datetime.date,
                       notes: str | None = None,
                       transfer_pair_id: int | None = None) -> Transaction:
    tx = Transaction(
        account_id=account_id,
        amount=amount,
        type=type_,
        description=description,
        notes=notes,
        date=date,
        transfer_pair_id=transfer_pair_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def update_transaction(db: Session, transaction_id: int,
                       **kwargs) -> Transaction | None:
    tx = get_transaction(db, transaction_id)
    if tx is None:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(tx, key, value)
    if "amount" in kwargs and kwargs["amount"] is not None:
        tx.amount = kwargs["amount"]
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, transaction_id: int) -> bool:
    tx = get_transaction(db, transaction_id)
    if tx is None:
        return False
    db.delete(tx)
    db.commit()
    return True


def create_transfer(db: Session, from_account_id: int, to_account_id: int,
                    amount: Decimal, description: str, date: datetime.date,
                    notes: str | None = None) -> tuple[Transaction, Transaction]:

    out_tx = Transaction(
        account_id=from_account_id,
        amount=-amount,
        type=TransactionType.TRANSFER,
        description=description,
        notes=notes,
        date=date,
        transfer_pair_id=None,
    )
    db.add(out_tx)
    db.flush()

    in_tx = Transaction(
        account_id=to_account_id,
        amount=amount,
        type=TransactionType.TRANSFER,
        description=description,
        notes=notes,
        date=date,
        transfer_pair_id=out_tx.id,
    )
    db.add(in_tx)
    db.flush()

    out_tx.transfer_pair_id = in_tx.id
    db.commit()
    db.refresh(out_tx)
    db.refresh(in_tx)
    return out_tx, in_tx


def compute_account_balance(account: Account, db: Session) -> Decimal:
    result = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.account_id == account.id
    ).scalar()
    return account.opening_balance + result


def get_recent_transactions(db: Session, limit: int = 10) -> list[Transaction]:
    return db.query(Transaction).order_by(
        Transaction.date.desc(), Transaction.created_at.desc()
    ).limit(limit).all()
