from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.crud.account import list_accounts
from app.crud.category import list_categories
from app.crud.recurring import (
    create_rule,
    delete_rule,
    get_rule,
    list_rules,
    update_rule,
)
from app.deps import get_current_user, get_db
from app.models.recurring import RecurringFrequency
from app.schemas.recurring import RecurringRuleCreate, RecurringRuleRead, RecurringRuleUpdate
from app.services.recurring import materialize_all, next_occurrences
from app.templates import templates
from app.utils import is_htmx, parse_date_or_422

router = APIRouter()


@router.get("/recurring", response_class=HTMLResponse)
async def recurring_list_page(
    request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    rules = list_rules(db, user_id=user.id)
    previews: dict[int, list[str]] = {}
    for rule in rules:
        dates = next_occurrences(rule, count=5)
        previews[rule.id] = [d.isoformat() for d in dates]
    return templates.TemplateResponse(
        request,
        "recurring/list.html",
        {"title": "Recurring Rules", "rules": rules, "previews": previews},
    )


@router.get("/recurring/new", response_class=HTMLResponse)
async def recurring_create_page(
    request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    accounts = list_accounts(db, user_id=user.id)
    categories = list_categories(db, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "recurring/form.html",
        {
            "title": "New Recurring Rule",
            "mode": "create",
            "rule": None,
            "accounts": accounts,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
        },
    )


@router.get("/recurring/{rule_id}/edit", response_class=HTMLResponse)
async def recurring_edit_page(
    request: Request, rule_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    rule = get_rule(db, rule_id, user_id=user.id)
    if rule is None:
        return HTMLResponse("Rule not found", status_code=404)
    accounts = list_accounts(db, user_id=user.id)
    categories = list_categories(db, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "recurring/form.html",
        {
            "title": "Edit Recurring Rule",
            "mode": "edit",
            "rule": rule,
            "accounts": accounts,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
        },
    )


@router.post("/recurring")
async def recurring_create(
    request: Request,
    account_id: int = Form(...),
    category_id: int | None = Form(None),
    amount: Decimal = Form(...),
    type: str = Form(...),
    description: str = Form(...),
    frequency: RecurringFrequency = Form(...),
    interval: int = Form(1),
    start_date: str = Form(...),
    end_date: str | None = Form(None),
    day_of_month: str | None = Form(None),
    day_of_week: str | None = Form(None),
    is_active: str = Form("true"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    if type not in ("expense", "income"):
        raise HTTPException(status_code=422, detail="Type must be expense or income")

    parsed_start = parse_date_or_422(start_date, "start_date")
    parsed_end = parse_date_or_422(end_date, "end_date") if end_date else None
    parsed_day_of_month = int(day_of_month) if day_of_month else None
    parsed_day_of_week = int(day_of_week) if day_of_week else None
    is_active_bool = is_active.lower() == "true"

    data = RecurringRuleCreate(
        account_id=account_id,
        category_id=category_id,
        amount=amount,
        type=type,
        description=description,
        frequency=frequency,
        interval=interval,
        start_date=parsed_start,
        end_date=parsed_end,
        day_of_month=parsed_day_of_month,
        day_of_week=parsed_day_of_week,
        is_active=is_active_bool,
    )
    rule = create_rule(db, data, user_id=user.id)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/recurring"})
    return RecurringRuleRead.model_validate(rule)


@router.patch("/recurring/{rule_id}")
async def recurring_update(
    request: Request,
    rule_id: int,
    account_id: int | None = Form(None),
    category_id: int | None = Form(None),
    amount: Decimal | None = Form(None),
    type: str | None = Form(None),
    description: str | None = Form(None),
    frequency: RecurringFrequency | None = Form(None),
    interval: int | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    day_of_month: str | None = Form(None),
    day_of_week: str | None = Form(None),
    is_active: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if amount is not None and amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    if type is not None and type not in ("expense", "income"):
        raise HTTPException(status_code=422, detail="Type must be expense or income")

    parsed_start = parse_date_or_422(start_date or None, "start_date")
    parsed_end = parse_date_or_422(end_date or None, "end_date")

    patch: dict[str, object] = {}
    if account_id is not None:
        patch["account_id"] = account_id
    if category_id is not None:
        patch["category_id"] = category_id
    if amount is not None:
        patch["amount"] = amount
    if type is not None:
        patch["type"] = type
    if description is not None:
        patch["description"] = description
    if frequency is not None:
        patch["frequency"] = frequency
    if interval is not None:
        patch["interval"] = interval
    if parsed_start is not None:
        patch["start_date"] = parsed_start
    if parsed_end is not None:
        patch["end_date"] = parsed_end
    if day_of_month:
        patch["day_of_month"] = int(day_of_month)
    if day_of_week:
        patch["day_of_week"] = int(day_of_week)
    if is_active is not None:
        patch["is_active"] = is_active.lower() == "true"

    data = RecurringRuleUpdate(**patch)
    rule = update_rule(db, rule_id, data, user_id=user.id)
    if rule is None:
        return HTMLResponse("Rule not found", status_code=404)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/recurring"})
    return RecurringRuleRead.model_validate(rule)


@router.delete("/recurring/{rule_id}")
async def recurring_delete(
    request: Request,
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ok, error_msg = delete_rule(db, rule_id, user_id=user.id)
    if not ok:
        if error_msg == "Rule not found":
            return HTMLResponse("Rule not found", status_code=404)
        if is_htmx(request):
            return HTMLResponse(error_msg, status_code=409)
        raise HTTPException(status_code=409, detail=error_msg)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Trigger": "recurring-rule-deleted"})
    return HTMLResponse(status_code=200)


@router.get("/api/recurring", response_model=list[RecurringRuleRead])
async def recurring_list_json(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list_rules(db, user_id=user.id)


@router.get("/api/recurring/{rule_id}", response_model=RecurringRuleRead)
async def recurring_get_json(
    rule_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    rule = get_rule(db, rule_id, user_id=user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.get("/api/recurring/{rule_id}/preview")
async def recurring_preview(
    rule_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    rule = get_rule(db, rule_id, user_id=user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    dates = next_occurrences(rule, count=5)
    return {"rule_id": rule_id, "next_dates": [d.isoformat() for d in dates]}


@router.post("/api/recurring/materialize")
async def recurring_materialize(db: Session = Depends(get_db), user=Depends(get_current_user)):
    results = materialize_all(db, user_id=user.id)
    total = sum(results.values())
    return {"total_materialized": total, "per_rule": results}
