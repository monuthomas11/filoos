"""Data export route — right to data portability (GDPR Art. 20)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.crud.user import get_all_user_data
from app.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()


@router.get("/api/account/export")
async def export_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export all user data as JSON — right to data portability (GDPR Art. 20)."""
    data = get_all_user_data(db, user.id)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="filoos-export.json"'},
    )
