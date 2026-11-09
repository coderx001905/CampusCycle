from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.authorization import get_current_user, require_platform_admin
from app.db.session import get_db
from app.models import User
from app.services.analytics import (
    get_category_analytics,
    get_college_analytics,
    get_request_analytics,
    get_summary_analytics,
    get_transfer_analytics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    data = get_summary_analytics(db, actor=user)
    return {"success": True, "data": data}


@router.get("/categories")
def analytics_categories(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    data = get_category_analytics(db, actor=user)
    return {"success": True, "data": data}


@router.get("/transfers")
def analytics_transfers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    data = get_transfer_analytics(db, actor=user)
    return {"success": True, "data": data}


@router.get("/requests")
def analytics_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    data = get_request_analytics(db, actor=user)
    return {"success": True, "data": data}


@router.get("/colleges")
def analytics_colleges(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    data = get_college_analytics(db, actor=admin)
    return {"success": True, "data": data}
