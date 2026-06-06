"""Transaction CRUD routes — HTML pages, HTMX partials, and JSON API."""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.crud.account import (
    list_accounts,
)
from app.crud.category import get_category, list_categories
from app.crud.transaction import (
    create_transaction,
    create_transfer,
    delete_transaction,
    delete_transfer_pair,
    get_transaction,
    list_transactions,
    update_transaction,
    update_transfer_pair,
)
from app.deps import get_db
from app.models.transaction import TransactionType
from app.schemas.transaction import TransactionRead
from app.templates import templates
from app.utils import is_htmx, parse_date_or_422

router = APIRouter()


def _get_amount_sign(type_: TransactionType) -> int:
    return -1 if type_ == TransactionType.EXPENSE else 1


def _safe_next(value: str | None) -> str | None:
    """Validate a `next` redirect target. Allow only same-origin absolute paths."""
    if not value or not isinstance(value, str):
        return None
    if not value.startswith("/") or value.startswith("//"):
        return None
    return value


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _render_list_items(request: Request, db: Session, **filters):
    txns = list_transactions(db, **filters)
    # Build a map of transfer_pair_id -> paired account name for transfer display
    paired_accounts: dict[int, str] = {}
    for tx in txns:
        if tx.type == TransactionType.TRANSFER and tx.transfer_pair_id is not None:
            pair_tx = get_transaction(db, tx.transfer_pair_id)
            if pair_tx is not None and pair_tx.account is not None:
                paired_accounts[tx.id] = pair_tx.account.name
    return templates.TemplateResponse(
        request,
        "partials/transaction_list_items.html",
        {"transactions": txns, "paired_accounts": paired_accounts},
    )


# ------------------------------------------------------------------
# HTML pages
# ------------------------------------------------------------------


@router.get("/transactions", response_class=HTMLResponse)
async def transaction_list_page(
    request: Request,
    account_id: str | None = Query(None, alias="account"),
    type_filter: str | None = Query(None, alias="type"),
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    description: str | None = Query(None, alias="q"),
    db: Session = Depends(get_db),
):
    parsed_account_id = None
    if account_id:
        try:
            parsed_account_id = int(account_id)
        except ValueError:
            pass

    parsed_type = None
    if type_filter:
        try:
            parsed_type = TransactionType(type_filter)
        except ValueError:
            pass

    parsed_date_from = None
    if date_from:
        try:
            parsed_date_from = datetime.date.fromisoformat(date_from)
        except ValueError:
            pass

    parsed_date_to = None
    if date_to:
        try:
            parsed_date_to = datetime.date.fromisoformat(date_to)
        except ValueError:
            pass

    filters = {}
    if parsed_account_id is not None:
        filters["account_id"] = parsed_account_id
    if parsed_type is not None:
        filters["type_filter"] = parsed_type
    if parsed_date_from is not None:
        filters["date_from"] = parsed_date_from
    if parsed_date_to is not None:
        filters["date_to"] = parsed_date_to
    if description:
        filters["description"] = description

    txns = list_transactions(db, **filters)
    accounts = list_accounts(db)

    # Build a map of transfer_pair_id -> paired account name for transfer display
    paired_accounts: dict[int, str] = {}
    for tx in txns:
        if tx.type == TransactionType.TRANSFER and tx.transfer_pair_id is not None:
            pair_tx = get_transaction(db, tx.transfer_pair_id)
            if pair_tx is not None and pair_tx.account is not None:
                paired_accounts[tx.id] = pair_tx.account.name

    if is_htmx(request):
        return templates.TemplateResponse(
            request,
            "partials/transaction_list_items.html",
            {"transactions": txns, "paired_accounts": paired_accounts},
        )

    return templates.TemplateResponse(
        request,
        "transactions/list.html",
        {
            "title": "Transactions",
            "transactions": txns,
            "accounts": accounts,
            "paired_accounts": paired_accounts,
            "filter_account_id": parsed_account_id,
            "filter_type": type_filter,
            "filter_date_from": date_from or "",
            "filter_date_to": date_to or "",
            "filter_description": description or "",
        },
    )


@router.get("/transactions/new", response_class=HTMLResponse)
async def transaction_create_page(
    request: Request,
    from_: str | None = Query(None, alias="from"),
    db: Session = Depends(get_db),
):
    accounts = list_accounts(db)
    categories = list_categories(db)
    return templates.TemplateResponse(
        request,
        "transactions/form.html",
        {
            "title": "New Transaction",
            "mode": "create",
            "transaction": None,
            "accounts": accounts,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
            "next_url": _safe_next(from_),
        },
    )


@router.get("/transactions/{transaction_id}/edit", response_class=HTMLResponse)
async def transaction_edit_page(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
):
    # TODO: support `next` param like the create page does (Phase 4.1 scope excluded edits)
    tx = get_transaction(db, transaction_id)
    if tx is None:
        return HTMLResponse("Transaction not found", status_code=404)

    accounts = list_accounts(db)
    categories = list_categories(db)

    # For transfers, find the paired transaction to get from/to account IDs
    from_account_id = None
    to_account_id = None
    if tx.type == TransactionType.TRANSFER and tx.transfer_pair_id is not None:
        pair_tx = get_transaction(db, tx.transfer_pair_id)
        if pair_tx is not None:
            if tx.amount < 0:
                from_account_id = tx.account_id
                to_account_id = pair_tx.account_id
            else:
                from_account_id = pair_tx.account_id
                to_account_id = tx.account_id

    return templates.TemplateResponse(
        request,
        "transactions/form.html",
        {
            "title": "Edit Transaction",
            "mode": "edit",
            "transaction": tx,
            "accounts": accounts,
            "categories": categories,
            "today": datetime.date.today().isoformat(),
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
        },
    )


# ------------------------------------------------------------------
# Mutations — HTMX partials with JSON fallback
# ------------------------------------------------------------------


@router.post("/transactions")
async def transaction_create(
    request: Request,
    type: str = Form(...),
    amount: Decimal = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    notes: str | None = Form(None),
    account_id: int | None = Form(None),
    category_id: int | None = Form(None),
    from_account_id: int | None = Form(None),
    to_account_id: int | None = Form(None),
    next: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        parsed_type = TransactionType(type)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid transaction type") from None
    parsed_date = parse_date_or_422(date)
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")

    if parsed_type == TransactionType.TRANSFER:
        if from_account_id is None or to_account_id is None:
            raise HTTPException(
                status_code=422,
                detail="Transfer requires from_account_id and to_account_id",
            )
        if from_account_id == to_account_id:
            raise HTTPException(
                status_code=422,
                detail="From and to accounts must be different",
            )
        out_tx, in_tx = create_transfer(
            db=db,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            description=description,
            date=parsed_date,
            notes=notes or None,
        )
        # For HTMX, return the outgoing leg row (or both — just render one)
        tx = out_tx
    else:
        if account_id is None:
            raise HTTPException(
                status_code=422, detail="account_id is required"
            )
        signed_amount = amount * _get_amount_sign(parsed_type)
        if category_id is not None:
            cat = get_category(db, category_id)
            if cat is None:
                raise HTTPException(status_code=422, detail="Category not found")
            expected = "expense" if parsed_type == TransactionType.EXPENSE else "income"
            if cat.type.value != expected:
                raise HTTPException(
                    status_code=422,
                    detail=f"Category type must be {expected}",
                )
        tx = create_transaction(
            db=db,
            account_id=account_id,
            amount=signed_amount,
            type_=parsed_type,
            description=description,
            date=parsed_date,
            notes=notes or None,
            category_id=category_id,
        )

    if is_htmx(request):
        redirect_target = _safe_next(next) or "/transactions"
        return Response(status_code=200, headers={"HX-Redirect": redirect_target})
    return TransactionRead.model_validate(tx)


@router.patch("/transactions/{transaction_id}")
async def transaction_update(
    request: Request,
    transaction_id: int,
    type: str | None = Form(None),
    amount: Decimal | None = Form(None),
    description: str | None = Form(None),
    date: str | None = Form(None),
    notes: str | None = Form(None),
    account_id: int | None = Form(None),
    category_id: int | None = Form(None),
    from_account_id: int | None = Form(None),
    to_account_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    # TODO: accept `next` form field and use `_safe_next` for redirect (Phase 4.1 scope excluded edits)
    existing = get_transaction(db, transaction_id)
    if existing is None:
        return HTMLResponse("Transaction not found", status_code=404)

    # Handle transfer edits — update both legs atomically
    if existing.type == TransactionType.TRANSFER:
        # Parse date if provided
        parsed_date = parse_date_or_422(date) if date is not None else None

        # Validate amount if provided
        if amount is not None and amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive")

        # Validate accounts are different if both provided
        if from_account_id is not None and to_account_id is not None:
            if from_account_id == to_account_id:
                raise HTTPException(
                    status_code=422,
                    detail="From and to accounts must be different",
                )

        result = update_transfer_pair(
            db=db,
            transaction_id=transaction_id,
            amount=amount,
            description=description,
            date=parsed_date,
            notes=notes,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
        )
        if result is None:
            return HTMLResponse("Transfer not found", status_code=404)

        out_tx, in_tx = result
        if is_htmx(request):
            return Response(status_code=200, headers={"HX-Redirect": "/transactions"})
        return TransactionRead.model_validate(out_tx)

    # Handle regular transaction edits
    patch: dict[str, object] = {}

    if type is not None:
        try:
            patch["type"] = TransactionType(type)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid transaction type") from None
    if amount is not None:
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be positive")
        tx_type = patch.get("type")
        if tx_type is None:
            tx_type = existing.type
        sign = _get_amount_sign(tx_type)
        patch["amount"] = amount * sign
    if description is not None:
        patch["description"] = description
    if date is not None:
        patch["date"] = parse_date_or_422(date)
    if notes is not None:
        patch["notes"] = notes or None
    if account_id is not None:
        patch["account_id"] = account_id
    # Always set category_id (including None to allow clearing)
    if category_id is not None:
        cat = get_category(db, category_id)
        if cat is None:
            raise HTTPException(status_code=422, detail="Category not found")
        tx_type = patch.get("type") or existing.type
        expected = "expense" if tx_type == TransactionType.EXPENSE else "income"
        if cat.type.value != expected:
            raise HTTPException(
                status_code=422,
                detail=f"Category type must be {expected}",
            )
    patch["category_id"] = category_id

    tx = update_transaction(db, transaction_id, **patch)
    if tx is None:
        return HTMLResponse("Transaction not found", status_code=404)

    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/transactions"})
    return TransactionRead.model_validate(tx)


@router.delete("/transactions/{transaction_id}")
async def transaction_delete(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
):
    tx = get_transaction(db, transaction_id)
    if tx is None:
        return HTMLResponse("Transaction not found", status_code=404)

    # For transfers, delete both legs
    if tx.type == TransactionType.TRANSFER:
        ok = delete_transfer_pair(db, transaction_id)
    else:
        ok = delete_transaction(db, transaction_id)

    if not ok:
        return HTMLResponse("Transaction not found", status_code=404)

    if is_htmx(request):
        return Response(
            status_code=200,
            headers={"HX-Trigger": "transaction-deleted"},
        )
    return RedirectResponse(url="/transactions", status_code=303)


# ------------------------------------------------------------------
# JSON API
# ------------------------------------------------------------------


@router.get("/api/transactions", response_model=list[TransactionRead])
async def transaction_list_json(
    account_id: str | None = Query(None, alias="account"),
    type_filter: str | None = Query(None, alias="type"),
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    limit: int = Query(100, alias="limit"),
    offset: int = Query(0, alias="offset"),
    db: Session = Depends(get_db),
):
    parsed_account_id = None
    if account_id:
        try:
            parsed_account_id = int(account_id)
        except ValueError:
            pass

    parsed_type = None
    if type_filter:
        try:
            parsed_type = TransactionType(type_filter)
        except ValueError:
            pass

    parsed_date_from = None
    if date_from:
        try:
            parsed_date_from = datetime.date.fromisoformat(date_from)
        except ValueError:
            pass

    parsed_date_to = None
    if date_to:
        try:
            parsed_date_to = datetime.date.fromisoformat(date_to)
        except ValueError:
            pass

    filters: dict = {"limit": limit, "offset": offset}
    if parsed_account_id is not None:
        filters["account_id"] = parsed_account_id
    if parsed_type is not None:
        filters["type_filter"] = parsed_type
    if parsed_date_from is not None:
        filters["date_from"] = parsed_date_from
    if parsed_date_to is not None:
        filters["date_to"] = parsed_date_to

    return list_transactions(db, **filters)


@router.get("/api/transactions/{transaction_id}", response_model=TransactionRead)
async def transaction_get_json(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    tx = get_transaction(db, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx
