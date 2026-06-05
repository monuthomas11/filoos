from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.models.recurring import RecurringRule
from app.schemas.recurring import RecurringRuleCreate, RecurringRuleUpdate


def list_rules(db: Session, active_only: bool = False) -> list[RecurringRule]:
    q = db.query(RecurringRule)
    if active_only:
        q = q.filter(RecurringRule.is_active.is_(True))
    return q.order_by(RecurringRule.created_at).all()


def get_rule(db: Session, rule_id: int) -> RecurringRule | None:
    return db.query(RecurringRule).filter(RecurringRule.id == rule_id).first()


def create_rule(db: Session, data: RecurringRuleCreate) -> RecurringRule:
    rule = RecurringRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: int, data: RecurringRuleUpdate) -> RecurringRule | None:
    rule = get_rule(db, rule_id)
    if rule is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> tuple[bool, str | None]:
    rule = get_rule(db, rule_id)
    if rule is None:
        return False, "Rule not found"
    db.delete(rule)
    db.commit()
    return True, None


def update_last_generated_date(db: Session, rule_id: int, date: datetime.date) -> RecurringRule | None:
    rule = get_rule(db, rule_id)
    if rule is None:
        return None
    rule.last_generated_date = date
    db.commit()
    db.refresh(rule)
    return rule
