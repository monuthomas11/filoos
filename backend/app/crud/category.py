"""CRUD helpers for the Category model."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def list_categories(db: Session, type_filter: str | None = None) -> list[Category]:
    q = db.query(Category)
    if type_filter:
        q = q.filter(Category.type == type_filter)
    return q.order_by(Category.name).all()


def get_category(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def create_category(db: Session, data: CategoryCreate) -> Category:
    payload = data.model_dump()
    if payload.get("color") is None:
        # Default purple if no color provided
        payload["color"] = "#7c3aed"
    category = Category(**payload)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, category_id: int, data: CategoryUpdate
) -> Category | None:
    category = get_category(db, category_id)
    if category is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> tuple[bool, str | None]:
    """Delete a category. Returns (success, error_message).
    Blocks deletion if the category has transactions.
    """
    category = get_category(db, category_id)
    if category is None:
        return False, "Category not found"
    if category.transactions:
        return False, "Cannot delete category with existing transactions"
    db.delete(category)
    db.commit()
    return True, None
