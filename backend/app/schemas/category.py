"""Pydantic schemas for Category CRUD."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.category import CategoryType


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CategoryType
    color: str | None = Field(None, max_length=7)
    icon: str | None = Field(None, max_length=50)
    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    type: CategoryType | None = None
    color: str | None = Field(None, max_length=7)
    icon: str | None = Field(None, max_length=50)
    parent_id: int | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: CategoryType
    color: str | None = None
    icon: str | None = None
    parent_id: int | None = None
