"""Account CRUD routes — HTML pages, HTMX partials, and JSON API."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.crud.account import (
    compute_balance,
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from app.deps import get_current_user, get_db
from app.models.account import AccountType
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.templates import templates
from app.utils import is_htmx

router = APIRouter()


# ------------------------------------------------------------------
# HTML pages
# ------------------------------------------------------------------


@router.get("/accounts", response_class=HTMLResponse)
async def account_list_page(
    request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    accounts = list_accounts(db, user_id=user.id)
    balances: dict[int, Decimal] = {}
    for a in accounts:
        balances[a.id] = compute_balance(a, db)
    return templates.TemplateResponse(
        request,
        "accounts/list.html",
        {"title": "Accounts", "accounts": accounts, "balances": balances},
    )


@router.get("/accounts/new", response_class=HTMLResponse)
async def account_create_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        request,
        "accounts/form.html",
        {"title": "New Account", "mode": "create", "account": None},
    )


@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse)
async def account_edit_page(
    request: Request, account_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    account = get_account(db, account_id, user_id=user.id)
    if account is None:
        return HTMLResponse("Account not found", status_code=404)
    return templates.TemplateResponse(
        request,
        "accounts/form.html",
        {"title": "Edit Account", "mode": "edit", "account": account},
    )


# ------------------------------------------------------------------
# Mutations — HTMX partials with JSON fallback
# ------------------------------------------------------------------


@router.post("/accounts")
async def account_create(
    request: Request,
    name: str = Form(...),
    type: AccountType = Form(...),
    currency: str = Form("INR"),
    opening_balance: Decimal = Form(Decimal("0.00")),
    color: str | None = Form(None),
    icon: str | None = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        data = AccountCreate(
            name=name,
            type=type,
            currency=currency,
            opening_balance=opening_balance,
            color=color or None,
            icon=icon or None,
            is_active=is_active,
        )
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    account = create_account(db, data, user_id=user.id)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/accounts"})
    return _respond_with_card(request, account, db)


@router.patch("/accounts/{account_id}")
async def account_update(
    request: Request,
    account_id: int,
    name: str | None = Form(None),
    type: AccountType | None = Form(None),
    currency: str | None = Form(None),
    opening_balance: Decimal | None = Form(None),
    color: str | None = Form(None),
    icon: str | None = Form(None),
    is_active: bool | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Only include non-None fields so that exclude_unset works correctly
    # (Form defaults to None for absent fields, but we don't want to
    # write None into the database — that would violate NOT NULL).
    patch: dict[str, object] = {}
    if name is not None:
        patch["name"] = name
    if type is not None:
        patch["type"] = type
    if currency is not None:
        patch["currency"] = currency
    if opening_balance is not None:
        patch["opening_balance"] = opening_balance
    if color is not None:
        patch["color"] = color
    if icon is not None:
        patch["icon"] = icon
    if is_active is not None:
        patch["is_active"] = is_active

    data = AccountUpdate(**patch)
    account = update_account(db, account_id, data, user_id=user.id)
    if account is None:
        return HTMLResponse("Account not found", status_code=404)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/accounts"})
    return _respond_with_card(request, account, db)


@router.delete("/accounts/{account_id}")
async def account_delete(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ok, error_msg = delete_account(db, account_id, user_id=user.id)
    if not ok:
        if error_msg == "Account not found":
            return HTMLResponse("Account not found", status_code=404)
        # Has transactions — block deletion
        if is_htmx(request):
            return HTMLResponse(
                "Cannot delete account with existing transactions. Remove all transactions first.",
                status_code=409,
            )
        raise HTTPException(
            status_code=409,
            detail="Cannot delete account with existing transactions",
        )
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Trigger": "account-deleted"})
    return RedirectResponse(url="/accounts", status_code=303)


# ------------------------------------------------------------------
# JSON API
# ------------------------------------------------------------------


@router.get("/api/accounts", response_model=list[AccountRead])
async def account_list_json(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list_accounts(db, user_id=user.id)


@router.get("/api/accounts/{account_id}", response_model=AccountRead)
async def account_get_json(
    account_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    account = get_account(db, account_id, user_id=user.id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/api/accounts/{account_id}/balance")
async def account_balance_json(
    account_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    account = get_account(db, account_id, user_id=user.id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account_id, "balance": str(compute_balance(account, db))}


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _respond_with_card(request: Request, account, db: Session):
    balance = compute_balance(account, db)
    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "partials/account_card.html",
            {"account": account, "balance": balance},
        )
    return AccountRead.model_validate(account)
