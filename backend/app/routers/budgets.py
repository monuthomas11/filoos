"""Budget CRUD routes — HTML pages, HTMX partials, and JSON API."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.crud.budget import (
    create_budget,
    delete_budget,
    get_budget,
    list_budgets,
    update_budget,
)
from app.crud.category import list_categories
from app.deps import get_db
from app.models.budget import BudgetPeriod
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate
from app.services.analytics import budget_progress
from app.templates import templates
from app.utils import is_htmx, parse_date_or_422

router = APIRouter()


# ------------------------------------------------------------------
# HTML pages
# ------------------------------------------------------------------


@router.get("/budgets", response_class=HTMLResponse)
async def budget_list_page(request: Request, db: Session = Depends(get_db)):
    budgets = list_budgets(db)
    today = datetime.date.today()
    progress = budget_progress(db, today.year, today.month)
    progress_map = {p["budget_id"]: p for p in progress}
    return templates.TemplateResponse(
        request,
        "budgets/list.html",
        {
            "title": "Budgets",
            "budgets": budgets,
            "progress": progress_map,
            "today": today,
        },
    )


@router.get("/budgets/new", response_class=HTMLResponse)
async def budget_create_page(request: Request, db: Session = Depends(get_db)):
    categories = list_categories(db)
    return templates.TemplateResponse(
        request,
        "budgets/form.html",
        {
            "title": "New Budget",
            "mode": "create",
            "budget": None,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
        },
    )


@router.get("/budgets/{budget_id}/edit", response_class=HTMLResponse)
async def budget_edit_page(
    request: Request, budget_id: int, db: Session = Depends(get_db)
):
    budget = get_budget(db, budget_id)
    if budget is None:
        return HTMLResponse("Budget not found", status_code=404)
    categories = list_categories(db)
    return templates.TemplateResponse(
        request,
        "budgets/form.html",
        {
            "title": "Edit Budget",
            "mode": "edit",
            "budget": budget,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
        },
    )


# ------------------------------------------------------------------
# Mutations — HTMX with JSON fallback
# ------------------------------------------------------------------


@router.post("/budgets")
async def budget_create(
    request: Request,
    category_id: int = Form(...),
    amount: Decimal = Form(...),
    period: BudgetPeriod = Form(...),
    start_date: str = Form(...),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
):
    parsed_date = parse_date_or_422(start_date, "start_date")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")

    data = BudgetCreate(
        category_id=category_id,
        amount=amount,
        period=period,
        start_date=parsed_date,
        is_active=is_active,
    )
    budget = create_budget(db, data)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/budgets"})
    return BudgetRead.model_validate(budget)


@router.patch("/budgets/{budget_id}")
async def budget_update(
    request: Request,
    budget_id: int,
    category_id: int | None = Form(None),
    amount: Decimal | None = Form(None),
    period: BudgetPeriod | None = Form(None),
    start_date: str | None = Form(None),
    is_active: bool | None = Form(None),
    db: Session = Depends(get_db),
):
    parsed_date = parse_date_or_422(start_date, "start_date") if start_date is not None else None

    patch: dict[str, object] = {}
    if category_id is not None:
        patch["category_id"] = category_id
    if amount is not None:
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive")
        patch["amount"] = amount
    if period is not None:
        patch["period"] = period
    if parsed_date is not None:
        patch["start_date"] = parsed_date
    if is_active is not None:
        patch["is_active"] = is_active

    data = BudgetUpdate(**patch)
    budget = update_budget(db, budget_id, data)
    if budget is None:
        return HTMLResponse("Budget not found", status_code=404)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/budgets"})
    return BudgetRead.model_validate(budget)


@router.delete("/budgets/{budget_id}")
async def budget_delete(
    request: Request,
    budget_id: int,
    db: Session = Depends(get_db),
):
    ok, error_msg = delete_budget(db, budget_id)
    if not ok:
        if error_msg == "Budget not found":
            return HTMLResponse("Budget not found", status_code=404)
        if is_htmx(request):
            return HTMLResponse(error_msg, status_code=409)
        raise HTTPException(status_code=409, detail=error_msg)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Trigger": "budget-deleted"})
    return HTMLResponse(status_code=200)


# ------------------------------------------------------------------
# JSON API
# ------------------------------------------------------------------


@router.get("/api/budgets", response_model=list[BudgetRead])
async def budget_list_json(db: Session = Depends(get_db)):
    return list_budgets(db)


@router.get("/api/budgets/{budget_id}", response_model=BudgetRead)
async def budget_get_json(budget_id: int, db: Session = Depends(get_db)):
    budget = get_budget(db, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget
