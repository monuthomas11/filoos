"""CRUD helpers for the Budget model."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetUpdate


def list_budgets(db: Session, active_only: bool = False) -> list[Budget]:
    q = db.query(Budget)
    if active_only:
        q = q.filter(Budget.is_active.is_(True))
    return q.order_by(Budget.created_at).all()


def get_budget(db: Session, budget_id: int) -> Budget | None:
    return db.query(Budget).filter(Budget.id == budget_id).first()


def create_budget(db: Session, data: BudgetCreate) -> Budget:
    budget = Budget(**data.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(
    db: Session, budget_id: int, data: BudgetUpdate
) -> Budget | None:
    budget = get_budget(db, budget_id)
    if budget is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(budget, key, value)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget_id: int) -> tuple[bool, str | None]:
    budget = get_budget(db, budget_id)
    if budget is None:
        return False, "Budget not found"
    db.delete(budget)
    db.commit()
    return True, None
