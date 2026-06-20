from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.models.recurring import RecurringRule
from app.schemas.recurring import RecurringRuleCreate, RecurringRuleUpdate


def list_rules(
    db: Session, active_only: bool = False, user_id: int | None = None
) -> list[RecurringRule]:
    q = db.query(RecurringRule)
    if user_id is not None:
        q = q.filter(RecurringRule.user_id == user_id)
    if active_only:
        q = q.filter(RecurringRule.is_active.is_(True))
    return q.order_by(RecurringRule.created_at).all()


def get_rule(db: Session, rule_id: int, user_id: int | None = None) -> RecurringRule | None:
    q = db.query(RecurringRule).filter(RecurringRule.id == rule_id)
    if user_id is not None:
        q = q.filter(RecurringRule.user_id == user_id)
    return q.first()


def create_rule(
    db: Session, data: RecurringRuleCreate, user_id: int | None = None
) -> RecurringRule:
    payload = data.model_dump()
    if user_id is not None:
        payload["user_id"] = user_id
    rule = RecurringRule(**payload)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(
    db: Session, rule_id: int, data: RecurringRuleUpdate, user_id: int | None = None
) -> RecurringRule | None:
    rule = get_rule(db, rule_id, user_id=user_id)
    if rule is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int, user_id: int | None = None) -> tuple[bool, str | None]:
    rule = get_rule(db, rule_id, user_id=user_id)
    if rule is None:
        return False, "Rule not found"
    db.delete(rule)
    db.commit()
    return True, None


def update_last_generated_date(
    db: Session, rule_id: int, date: datetime.date, user_id: int | None = None
) -> RecurringRule | None:
    rule = get_rule(db, rule_id, user_id=user_id)
    if rule is None:
        return None
    rule.last_generated_date = date
    db.commit()
    db.refresh(rule)
    return rule
