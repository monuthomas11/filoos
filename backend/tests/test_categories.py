"""Tests for the Category model, CRUD, and HTTP endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.category import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)
from app.models.category import CategoryType
from app.schemas.category import CategoryCreate, CategoryUpdate

# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------


def test_category_type_enum():
    assert CategoryType.EXPENSE.value == "expense"
    assert CategoryType.INCOME.value == "income"


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_create_and_read_category(db_session: Session):
    data = CategoryCreate(name="Groceries", type=CategoryType.EXPENSE, color="#16a34a")
    cat = create_category(db_session, data)
    assert cat.id is not None
    assert cat.name == "Groceries"
    assert cat.type == CategoryType.EXPENSE
    assert cat.color == "#16a34a"

    fetched = get_category(db_session, cat.id)
    assert fetched is not None
    assert fetched.name == "Groceries"


def test_create_category_default_color(db_session: Session):
    data = CategoryCreate(name="Default", type=CategoryType.INCOME)
    cat = create_category(db_session, data)
    assert cat.color == "#7c3aed"


def test_list_categories(db_session: Session):
    create_category(db_session, CategoryCreate(name="Food", type=CategoryType.EXPENSE))
    create_category(db_session, CategoryCreate(name="Salary", type=CategoryType.INCOME))
    assert len(list_categories(db_session)) == 2


def test_list_categories_filter_by_type(db_session: Session):
    create_category(db_session, CategoryCreate(name="Food", type=CategoryType.EXPENSE))
    create_category(db_session, CategoryCreate(name="Salary", type=CategoryType.INCOME))
    expense = list_categories(db_session, type_filter="expense")
    assert len(expense) == 1
    assert expense[0].name == "Food"


def test_update_category(db_session: Session):
    cat = create_category(db_session, CategoryCreate(name="Old", type=CategoryType.EXPENSE))
    updated = update_category(
        db_session, cat.id, CategoryUpdate(name="New", color="#dc2626")
    )
    assert updated is not None
    assert updated.name == "New"
    assert updated.color == "#dc2626"


def test_update_nonexistent_category(db_session: Session):
    result = update_category(db_session, 999, CategoryUpdate(name="Nope"))
    assert result is None


def test_delete_category(db_session: Session):
    cat = create_category(db_session, CategoryCreate(name="Delete Me", type=CategoryType.EXPENSE))
    ok, err = delete_category(db_session, cat.id)
    assert ok is True
    assert err is None
    assert get_category(db_session, cat.id) is None


def test_delete_nonexistent_category(db_session: Session):
    ok, err = delete_category(db_session, 999)
    assert ok is False
    assert err == "Category not found"


# ------------------------------------------------------------------
# HTTP — HTML pages
# ------------------------------------------------------------------


def test_category_list_page(client: TestClient):
    client.post("/categories", data={"name": "Food", "type": "expense"},
                headers={"HX-Request": "true"})
    response = client.get("/categories")
    assert response.status_code == 200
    assert "Food" in response.text


def test_category_new_page(client: TestClient):
    response = client.get("/categories/new")
    assert response.status_code == 200
    assert "Create category" in response.text


def test_category_edit_page(client: TestClient):
    client.post("/categories", data={"name": "Edit Me", "type": "expense"},
                headers={"HX-Request": "true"})
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]

    response = client.get(f"/categories/{cat_id}/edit")
    assert response.status_code == 200
    assert "Edit Me" in response.text
    assert "Save changes" in response.text


def test_category_edit_page_not_found(client: TestClient):
    response = client.get("/categories/99999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------
# HTTP — mutations
# ------------------------------------------------------------------


def test_create_category_via_htmx(client: TestClient):
    response = client.post(
        "/categories",
        data={"name": "Transport", "type": "expense", "color": "#d97706"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/categories"


def test_update_category_via_htmx(client: TestClient):
    client.post("/categories", data={"name": "Before", "type": "expense"},
                headers={"HX-Request": "true"})
    response = client.patch(
        "/categories/1",
        data={"name": "After"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/categories"


def test_delete_category_via_htmx(client: TestClient):
    client.post("/categories", data={"name": "Delete Me", "type": "expense"},
                headers={"HX-Request": "true"})
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]

    response = client.delete(
        f"/categories/{cat_id}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "category-deleted"


# ------------------------------------------------------------------
# HTTP — JSON API
# ------------------------------------------------------------------


def test_list_categories_json(client: TestClient):
    client.post("/categories", data={"name": "JSON Cat", "type": "income"},
                headers={"HX-Request": "true"})
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(c["name"] == "JSON Cat" for c in data)


def test_get_category_json(client: TestClient):
    client.post("/categories", data={"name": "Single", "type": "expense"},
                headers={"HX-Request": "true"})
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]

    response = client.get(f"/api/categories/{cat_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Single"


def test_get_category_json_not_found(client: TestClient):
    response = client.get("/api/categories/99999")
    assert response.status_code == 404


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


def test_create_category_empty_name_fails(client: TestClient):
    response = client.post(
        "/categories",
        data={"name": "", "type": "expense"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 422


def test_create_category_invalid_type_fails(client: TestClient):
    response = client.post(
        "/categories",
        data={"name": "Bad", "type": "invalid"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 422
