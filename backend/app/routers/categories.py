"""Category CRUD routes — HTML pages, HTMX partials, and JSON API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.crud.category import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)
from app.deps import get_current_user, get_db
from app.models.category import CategoryType
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.templates import templates
from app.utils import is_htmx

router = APIRouter()


# ------------------------------------------------------------------
# HTML pages
# ------------------------------------------------------------------


@router.get("/categories", response_class=HTMLResponse)
async def category_list_page(
    request: Request,
    type: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    categories = list_categories(db, type_filter=type, user_id=user.id)
    return templates.TemplateResponse(
        request,
        "categories/list.html",
        {"title": "Categories", "categories": categories, "filter_type": type or ""},
    )


@router.get("/categories/new", response_class=HTMLResponse)
async def category_create_page(request: Request):
    return templates.TemplateResponse(
        request,
        "categories/form.html",
        {"title": "New Category", "mode": "create", "category": None},
    )


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def category_edit_page(
    request: Request,
    category_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = get_category(db, category_id, user_id=user.id)
    if category is None:
        return HTMLResponse("Category not found", status_code=404)
    return templates.TemplateResponse(
        request,
        "categories/form.html",
        {"title": "Edit Category", "mode": "edit", "category": category},
    )


# ------------------------------------------------------------------
# Mutations — HTMX with JSON fallback
# ------------------------------------------------------------------


@router.post("/categories")
async def category_create(
    request: Request,
    name: str = Form(...),
    type: CategoryType = Form(...),
    color: str | None = Form(None),
    icon: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        data = CategoryCreate(
            name=name,
            type=type,
            color=color or None,
            icon=icon or None,
        )
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    category = create_category(db, data, user_id=user.id)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/categories"})
    return CategoryRead.model_validate(category)


@router.patch("/categories/{category_id}")
async def category_update(
    request: Request,
    category_id: int,
    name: str | None = Form(None),
    type: CategoryType | None = Form(None),
    color: str | None = Form(None),
    icon: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    patch: dict[str, object] = {}
    if name is not None:
        patch["name"] = name
    if type is not None:
        patch["type"] = type
    if color is not None:
        patch["color"] = color
    if icon is not None:
        patch["icon"] = icon

    data = CategoryUpdate(**patch)
    category = update_category(db, category_id, data, user_id=user.id)
    if category is None:
        return HTMLResponse("Category not found", status_code=404)
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": "/categories"})
    return CategoryRead.model_validate(category)


@router.delete("/categories/{category_id}")
async def category_delete(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ok, error_msg = delete_category(db, category_id, user_id=user.id)
    if not ok:
        if error_msg == "Category not found":
            return HTMLResponse("Category not found", status_code=404)
        if is_htmx(request):
            return HTMLResponse(
                "Cannot delete category with existing transactions. Remove all transactions first.",
                status_code=409,
            )
        raise HTTPException(
            status_code=409,
            detail="Cannot delete category with existing transactions",
        )
    if is_htmx(request):
        return Response(status_code=200, headers={"HX-Trigger": "category-deleted"})
    return HTMLResponse(status_code=200)


# ------------------------------------------------------------------
# JSON API
# ------------------------------------------------------------------


@router.get("/api/categories", response_model=list[CategoryRead])
async def category_list_json(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list_categories(db, user_id=user.id)


@router.get("/api/categories/{category_id}", response_model=CategoryRead)
async def category_get_json(
    category_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    category = get_category(db, category_id, user_id=user.id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
