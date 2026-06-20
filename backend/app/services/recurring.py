from __future__ import annotations

import datetime
import logging

from sqlalchemy.orm import Session

from app.crud.recurring import update_last_generated_date
from app.crud.transaction import create_transaction
from app.models.recurring import RecurringFrequency, RecurringRule, RecurringTransactionType
from app.models.transaction import TransactionType

logger = logging.getLogger("app.services.recurring")


def _next_date(
    after: datetime.date,
    frequency: RecurringFrequency,
    interval: int,
    day_of_month: int | None,
    day_of_week: int | None,
) -> datetime.date:
    if frequency == RecurringFrequency.DAILY:
        return after + datetime.timedelta(days=interval)

    if frequency == RecurringFrequency.WEEKLY:
        days_to_add = interval * 7
        result = after + datetime.timedelta(days=days_to_add)
        if day_of_week is not None:
            days_diff = day_of_week - result.weekday()
            if days_diff < 0:
                days_diff += 7
            result += datetime.timedelta(days=days_diff)
        return result

    if frequency == RecurringFrequency.MONTHLY:
        month = after.month + interval
        year = after.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = day_of_month or after.day
        max_day = _days_in_month(year, month)
        return datetime.date(year, month, min(day, max_day))

    if frequency == RecurringFrequency.YEARLY:
        year = after.year + interval
        month = after.month
        day = day_of_month if day_of_month is not None else after.day
        max_day = _days_in_month(year, month)
        return datetime.date(year, month, min(day, max_day))

    return after


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return (datetime.date(year + 1, 1, 1) - datetime.date(year, 12, 1)).days
    return (datetime.date(year, month + 1, 1) - datetime.date(year, month, 1)).days


def next_occurrences(rule: RecurringRule, count: int = 5) -> list[datetime.date]:
    dates: list[datetime.date] = []
    current = rule.last_generated_date or rule.start_date
    end = rule.end_date or datetime.date.max

    while len(dates) < count:
        next_d = _next_date(
            current,
            rule.frequency,
            rule.interval,
            rule.day_of_month,
            rule.day_of_week,
        )
        if next_d > end:
            break
        dates.append(next_d)
        current = next_d

    return dates


def materialize_rule(db: Session, rule: RecurringRule, user_id: int | None = None) -> int:
    today = datetime.date.today()
    current = rule.last_generated_date or rule.start_date
    end = min(rule.end_date or datetime.date.max, today)
    count = 0
    tx_user_id = user_id or rule.user_id

    while current < end:
        next_d = _next_date(
            current,
            rule.frequency,
            rule.interval,
            rule.day_of_month,
            rule.day_of_week,
        )
        if next_d > end:
            break

        create_transaction(
            db=db,
            account_id=rule.account_id,
            amount=(-rule.amount if rule.type == RecurringTransactionType.EXPENSE else rule.amount),
            type_=TransactionType(rule.type.value),
            description=rule.description,
            date=next_d,
            category_id=rule.category_id,
            recurring_rule_id=rule.id,
            user_id=tx_user_id,
            commit=False,
        )
        count += 1
        current = next_d

    if count > 0:
        db.commit()
        update_last_generated_date(db, rule.id, current)
        logger.info(
            "materialized recurring rule",
            extra={
                "rule_id": rule.id,
                "rule_description": rule.description,
                "generated": count,
                "up_to": current.isoformat(),
            },
        )
    else:
        logger.debug(
            "recurring rule up to date",
            extra={"rule_id": rule.id, "rule_description": rule.description},
        )

    return count


def materialize_all(db: Session, user_id: int | None = None) -> dict[int, int]:
    from app.crud.recurring import list_rules

    rules = list_rules(db, active_only=True, user_id=user_id)
    logger.info("materializing recurring rules", extra={"rule_count": len(rules)})
    results: dict[int, int] = {}
    for rule in rules:
        try:
            results[rule.id] = materialize_rule(db, rule, user_id=user_id)
        except Exception:
            logger.exception(
                "failed to materialize recurring rule",
                extra={"rule_id": rule.id, "rule_description": rule.description},
            )
            results[rule.id] = 0
    return results
