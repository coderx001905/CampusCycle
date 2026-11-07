import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authorization import (
    get_current_user,
    require_college_representative,
    require_platform_admin,
)
from app.core.passwords import hash_password
from app.db.session import get_db
from app.models import College, User
from app.schemas.accounts import (
    CollegeUpdate,
    CollegeVerificationUpdate,
    UserCreate,
    UserStatusUpdate,
    UserUpdate,
)
from app.services.auth import normalize_email, safe_user

router = APIRouter(tags=["colleges and users"])
logger = logging.getLogger(__name__)


def _college_payload(college: College) -> dict[str, object]:
    return {"id": college.id, "name": college.name, "address": college.address,
            "city": college.city, "contact_email": college.contact_email,
            "verification_status": college.verification_status,
            "created_at": college.created_at, "updated_at": college.updated_at}


@router.get("/colleges/me")
def college_me(user: User = Depends(require_college_representative),
               db: Session = Depends(get_db)) -> dict:
    college = db.get(College, user.college_id)
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")
    return {"success": True, "data": _college_payload(college)}


@router.patch("/colleges/me")
def update_college_me(payload: CollegeUpdate,
                      user: User = Depends(require_college_representative),
                      db: Session = Depends(get_db)) -> dict:
    values = payload.model_dump(exclude_unset=True)
    if not values or any(value is None for value in values.values()):
        raise HTTPException(status_code=422, detail="Provide at least one non-null college field.")
    college = db.get(College, user.college_id)
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")
    for field, value in values.items():
        setattr(college, field, str(value) if field == "contact_email" else value)
    db.commit()
    db.refresh(college)
    return {"success": True, "data": _college_payload(college)}


@router.get("/colleges")
def list_colleges(_admin: User = Depends(require_platform_admin),
                  db: Session = Depends(get_db), page: int = 1, page_size: int = 20) -> dict:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Invalid pagination values.")
    total = db.scalar(select(func.count()).select_from(College)) or 0
    colleges = db.scalars(select(College).order_by(College.id).offset((page - 1) * page_size).limit(page_size)).all()
    return {"success": True, "data": {"items": [_college_payload(item) for item in colleges],
                                      "page": page, "page_size": page_size, "total": total}}


@router.get("/colleges/{college_id}")
def get_college(college_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> dict:
    if user.role != "platform_admin" and user.college_id != college_id:
        raise HTTPException(status_code=404, detail="College not found.")
    college = db.get(College, college_id)
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")
    return {"success": True, "data": _college_payload(college)}


@router.patch("/admin/colleges/{college_id}/verification")
def update_college_verification(college_id: int, payload: CollegeVerificationUpdate,
                                admin: User = Depends(require_platform_admin),
                                db: Session = Depends(get_db)) -> dict:
    if payload.verification_status not in {"verified", "rejected"}:
        raise HTTPException(status_code=422, detail="Verification status must be verified or rejected.")
    college = db.get(College, college_id)
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")
    previous = college.verification_status
    college.verification_status = payload.verification_status
    db.commit()
    db.refresh(college)
    logger.info("College verification updated college_id=%s admin_user_id=%s from=%s to=%s",
                college.id, admin.id, previous, college.verification_status)
    return {"success": True, "data": _college_payload(college)}


@router.get("/users/me")
def user_me(user: User = Depends(get_current_user)) -> dict:
    return {"success": True, "data": safe_user(user)}


@router.patch("/users/me")
def update_user_me(payload: UserUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> dict:
    values = payload.model_dump(exclude_unset=True)
    if not values or any(value is None for value in values.values()):
        raise HTTPException(status_code=422, detail="Provide at least one non-null profile field.")
    for field, value in values.items():
        setattr(user, field, normalize_email(str(value)) if field == "email" else value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    db.refresh(user)
    return {"success": True, "data": safe_user(user)}


@router.get("/colleges/me/users")
def list_college_users(user: User = Depends(require_college_representative),
                       db: Session = Depends(get_db), page: int = 1,
                       page_size: int = 20) -> dict:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Invalid pagination values.")
    query = select(User).where(User.college_id == user.college_id,
                               User.role == "college_representative").order_by(User.id)
    total = db.scalar(select(func.count()).select_from(User).where(
        User.college_id == user.college_id, User.role == "college_representative")) or 0
    users = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {"success": True, "data": {"items": [safe_user(item) for item in users],
                                      "page": page, "page_size": page_size, "total": total}}


@router.post("/colleges/me/users", status_code=201)
def create_college_user(payload: UserCreate,
                        user: User = Depends(require_college_representative),
                        db: Session = Depends(get_db)) -> dict:
    created = User(college_id=user.college_id, name=payload.name,
                   email=normalize_email(str(payload.email)),
                   password_hash=hash_password(payload.password),
                   role="college_representative", is_active=True)
    db.add(created)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    db.refresh(created)
    return {"success": True, "data": safe_user(created)}


@router.patch("/users/{user_id}/status")
def update_user_status(user_id: int, payload: UserStatusUpdate,
                       actor: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> dict:
    # SQLite's immediate write lock serializes representative deactivation checks.
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    target = db.get(User, user_id)
    if target is None or (actor.role != "platform_admin" and
                          (actor.role != "college_representative" or target.college_id != actor.college_id)):
        db.rollback()
        raise HTTPException(status_code=404, detail="User not found.")
    if actor.role not in {"platform_admin", "college_representative"}:
        db.rollback()
        raise HTTPException(status_code=403, detail="Account management is not permitted.")
    if actor.role == "college_representative" and target.role != "college_representative":
        db.rollback()
        raise HTTPException(status_code=403, detail="Only representative account status can be changed.")
    if target.role == "college_representative" and target.is_active and not payload.is_active:
        count = db.scalar(select(func.count()).select_from(User).where(
            User.college_id == target.college_id,
            User.role == "college_representative", User.is_active.is_(True))) or 0
        if count <= 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="The last active college representative cannot be deactivated.")
    target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    return {"success": True, "data": safe_user(target)}
