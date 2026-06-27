"""CRUD helpers for the User model."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.recurring import RecurringRule
from app.models.transaction import Transaction
from app.models.user import User


def delete_user_by_id(db: Session, user_id: int) -> None:
    """Permanently delete a user and all associated data.

    Deletes in FK-safe order: transactions → recurring rules → budgets →
    accounts → categories → user.  The ordering is FK-coupled — if model
    relationships add non‑user_id foreign keys between these tables in the
    future, this function must be reviewed.
    """
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.query(RecurringRule).filter(RecurringRule.user_id == user_id).delete()
    db.query(Budget).filter(Budget.user_id == user_id).delete()
    db.query(Account).filter(Account.user_id == user_id).delete()
    db.query(Category).filter(Category.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()


def get_all_user_data(db: Session, user_id: int) -> dict:
    """Return all data belonging to a user, serialized for JSON export."""
    user = db.get(User, user_id)

    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    recurring_rules = db.query(RecurringRule).filter(RecurringRule.user_id == user_id).all()

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": {
            "email": user.email if user else None,
            "name": user.name if user else None,
            "created_at": user.created_at.isoformat() if user else None,
        },
        "accounts": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type.value,
                "currency": a.currency,
                "opening_balance": str(a.opening_balance),
                "color": a.color,
                "icon": a.icon,
                "is_active": a.is_active,
                "show_on_dashboard": a.show_on_dashboard,
                "include_in_total": a.include_in_total,
                "created_at": a.created_at.isoformat(),
            }
            for a in accounts
        ],
        "transactions": [
            {
                "id": t.id,
                "account_id": t.account_id,
                "category_id": t.category_id,
                "amount": str(t.amount),
                "type": t.type.value,
                "description": t.description,
                "notes": t.notes,
                "date": t.date.isoformat(),
                "transfer_pair_id": t.transfer_pair_id,
                "recurring_rule_id": t.recurring_rule_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type.value,
                "color": c.color,
                "icon": c.icon,
                "parent_id": c.parent_id,
            }
            for c in categories
        ],
        "budgets": [
            {
                "id": b.id,
                "category_id": b.category_id,
                "amount": str(b.amount),
                "period": b.period.value,
                "start_date": b.start_date.isoformat(),
                "is_active": b.is_active,
                "created_at": b.created_at.isoformat(),
            }
            for b in budgets
        ],
        "recurring_rules": [
            {
                "id": r.id,
                "account_id": r.account_id,
                "category_id": r.category_id,
                "amount": str(r.amount),
                "type": r.type.value,
                "description": r.description,
                "frequency": r.frequency.value,
                "interval": r.interval,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "day_of_month": r.day_of_month,
                "day_of_week": r.day_of_week,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat(),
            }
            for r in recurring_rules
        ],
    }
