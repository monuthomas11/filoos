"""CRUD helpers for the Budget model."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate


def list_budgets(
    db: Session, active_only: bool = False, user_id: int | None = None
) -> list[Budget]:
    q = db.query(Budget)
    if user_id is not None:
        q = q.filter(Budget.user_id == user_id)
    if active_only:
        q = q.filter(Budget.is_active.is_(True))
    return q.order_by(Budget.created_at).all()


def get_budget(db: Session, budget_id: int, user_id: int | None = None) -> Budget | None:
    q = db.query(Budget).filter(Budget.id == budget_id)
    if user_id is not None:
        q = q.filter(Budget.user_id == user_id)
    return q.first()


def create_budget(db: Session, data: BudgetCreate, user_id: int | None = None) -> Budget:
    payload = data.model_dump()
    if user_id is not None:
        payload["user_id"] = user_id
    budget = Budget(**payload)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(
    db: Session, budget_id: int, data: BudgetUpdate, user_id: int | None = None
) -> Budget | None:
    budget = get_budget(db, budget_id, user_id=user_id)
    if budget is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(budget, key, value)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(
    db: Session, budget_id: int, user_id: int | None = None
) -> tuple[bool, str | None]:
    budget = get_budget(db, budget_id, user_id=user_id)
    if budget is None:
        return False, "Budget not found"
    db.delete(budget)
    db.commit()
    return True, None
