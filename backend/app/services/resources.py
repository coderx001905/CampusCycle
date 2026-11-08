import logging
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.authorization import require_verified_college
from app.models import Request, Resource, User
from app.schemas.resources import ResourceCreate
from app.core.config import Settings
from app.services.resource_images import (
    ProcessedImage,
    remove_stored_image,
    safe_stored_image_path,
    store_processed_image,
)

logger = logging.getLogger(__name__)


def is_resource_owner(user: User, resource: Resource) -> bool:
    return user.role == "college_representative" and user.college_id == resource.college_id


def synchronize_depleted_status(resource: Resource) -> None:
    """Central depletion rule for later approved physical-stock workflows."""
    if resource.quantity_total == 0:
        resource.status = "depleted"


def resource_image_url(resource: Resource, settings: Settings) -> str | None:
    if safe_stored_image_path(settings, resource.image_path) is None:
        return None
    return f"/api/v1/resources/{resource.id}/image"


def marketplace_data(resource: Resource, settings: Settings) -> dict[str, object]:
    return {
        "id": resource.id,
        "name": resource.name,
        "description": resource.description,
        "category": resource.category,
        "condition": resource.condition,
        "quantity_available": resource.quantity_available,
        "unit": resource.unit,
        "transfer_type": resource.transfer_type,
        "indicative_price": resource.indicative_price,
        "status": resource.status,
        "image_url": resource_image_url(resource, settings),
        "college": {"id": resource.college.id, "name": resource.college.name,
                    "city": resource.college.city},
    }


def inventory_data(resource: Resource) -> dict[str, object]:
    return {
        "id": resource.id,
        "name": resource.name,
        "category": resource.category,
        "condition": resource.condition,
        "quantity_total": resource.quantity_total,
        "quantity_available": resource.quantity_available,
        "quantity_reserved": resource.quantity_reserved,
        "unit": resource.unit,
        "status": resource.status,
    }


def create_resource(db: Session, *, user: User, payload: ResourceCreate) -> Resource:
    if user.role != "college_representative" or user.college_id is None:
        raise HTTPException(status_code=403, detail="College representative access is required.")
    require_verified_college(db, user.college_id)
    resource = Resource(
        college_id=user.college_id,
        created_by_user_id=user.id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        condition=payload.condition,
        quantity_total=payload.quantity,
        quantity_available=payload.quantity,
        quantity_reserved=0,
        unit=payload.unit,
        transfer_type=payload.transfer_type,
        indicative_price=payload.indicative_price,
        status="active",
    )
    db.add(resource)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Resource data violates an approved inventory constraint.") from exc
    db.refresh(resource)
    return resource


def _filtered_resource_query(*, search: str | None, category: str | None,
                             condition: str | None, transfer_type: str | None,
                             college_id: int | None):
    query = select(Resource).options(joinedload(Resource.college)).where(
        Resource.status == "active", Resource.quantity_total > 0
    )
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        query = query.where(or_(Resource.name.ilike(pattern, escape="\\"),
                                Resource.description.ilike(pattern, escape="\\")))
    if category:
        query = query.where(func.lower(Resource.category) == category.lower())
    if condition:
        query = query.where(func.lower(Resource.condition) == condition.lower())
    if transfer_type:
        query = query.where(Resource.transfer_type == transfer_type)
    if college_id is not None:
        query = query.where(Resource.college_id == college_id)
    return query


def browse_resources(db: Session, *, search: str | None, category: str | None,
                     condition: str | None, transfer_type: str | None,
                     college_id: int | None, page: int, page_size: int) -> tuple[list[Resource], int]:
    query = _filtered_resource_query(search=search, category=category, condition=condition,
                                    transfer_type=transfer_type, college_id=college_id)
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Resource.created_at.desc(), Resource.id.desc())
                       .offset((page - 1) * page_size).limit(page_size)).all()
    return items, total


def get_visible_resource(db: Session, *, resource_id: int, user: User) -> Resource:
    resource = db.scalar(select(Resource).options(joinedload(Resource.college))
                         .where(Resource.id == resource_id))
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    if resource.status == "active" and resource.quantity_total > 0:
        return resource
    if is_resource_owner(user, resource):
        return resource
    raise HTTPException(status_code=404, detail="Resource not found.")


def get_owned_resource(db: Session, *, resource_id: int, user: User) -> Resource:
    if user.role != "college_representative" or user.college_id is None:
        raise HTTPException(status_code=403, detail="College representative access is required.")
    resource = db.scalar(select(Resource).options(joinedload(Resource.college)).where(
        Resource.id == resource_id, Resource.college_id == user.college_id
    ))
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return resource


def update_resource(db: Session, *, resource: Resource, changes: dict[str, object]) -> Resource:
    new_transfer_type = changes.get("transfer_type")
    if new_transfer_type is not None and new_transfer_type != resource.transfer_type:
        if resource.quantity_reserved > 0:
            raise HTTPException(
                status_code=409,
                detail="The transfer type cannot be changed while inventory is reserved.",
            )
        outstanding_statuses = ("pending", "approved", "in_progress", "awaiting_resolution")
        has_outstanding = db.scalar(
            select(Request.id)
            .where(
                or_(
                    Request.resource_id == resource.id,
                    Request.offered_resource_id == resource.id,
                ),
                Request.status.in_(outstanding_statuses),
            )
            .limit(1)
        )
        if has_outstanding is not None:
            raise HTTPException(
                status_code=409,
                detail="The transfer type cannot be changed while outstanding requests depend on this resource.",
            )
    for field, value in changes.items():
        setattr(resource, field, value)
    synchronize_depleted_status(resource)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Resource data violates an approved constraint.") from exc
    db.refresh(resource)
    return resource


def set_listing_status(db: Session, *, resource: Resource, requested_status: str) -> Resource:
    if requested_status == "active" and resource.quantity_total == 0:
        raise HTTPException(status_code=409, detail="A depleted resource cannot be activated without physical stock.")
    resource.status = requested_status
    synchronize_depleted_status(resource)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Resource status conflicts with inventory constraints.") from exc
    db.refresh(resource)
    return resource


def list_owned_inventory(db: Session, *, user: User) -> list[Resource]:
    if user.role != "college_representative" or user.college_id is None:
        raise HTTPException(status_code=403, detail="College representative access is required.")
    require_verified_college(db, user.college_id)
    return db.scalars(select(Resource).where(Resource.college_id == user.college_id)
                      .order_by(Resource.created_at.desc(), Resource.id.desc())).all()


def replace_resource_image(db: Session, *, resource: Resource, image: ProcessedImage,
                           settings: Settings) -> str:
    old_reference = resource.image_path
    new_reference = store_processed_image(image, settings)
    try:
        old_reference_filter = (Resource.image_path.is_(None) if old_reference is None
                                else Resource.image_path == old_reference)
        result = db.execute(
            update(Resource)
            .where(Resource.id == resource.id, old_reference_filter)
            .values(image_path=new_reference)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            db.rollback()
            remove_stored_image(settings, new_reference)
            db.refresh(resource)
            raise HTTPException(status_code=409, detail="The resource image changed during this upload. Retry the request.")
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        remove_stored_image(settings, new_reference)
        logger.exception("Resource image reference update failed resource_id=%s", resource.id)
        raise HTTPException(status_code=500, detail="Image could not be saved.") from exc
    if old_reference and old_reference != new_reference:
        if not remove_stored_image(settings, old_reference):
            logger.warning("Previous resource image cleanup failed resource_id=%s", resource.id)
    db.refresh(resource)
    return new_reference


def clear_resource_image(db: Session, *, resource: Resource, settings: Settings) -> None:
    old_reference = resource.image_path
    if old_reference is None:
        return
    try:
        result = db.execute(
            update(Resource)
            .where(Resource.id == resource.id, Resource.image_path == old_reference)
            .values(image_path=None)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            db.rollback()
            db.refresh(resource)
            raise HTTPException(status_code=409, detail="The resource image changed before removal. Retry the request.")
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Resource image removal failed resource_id=%s", resource.id)
        raise HTTPException(status_code=500, detail="Image could not be removed.") from exc
    if not remove_stored_image(settings, old_reference):
        logger.warning("Resource image cleanup failed resource_id=%s", resource.id)


def get_resource_image_path(db: Session, *, resource: Resource,
                            settings: Settings) -> tuple[Path, str] | None:
    path = safe_stored_image_path(settings, resource.image_path)
    if path is None:
        return None
    media_type = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix)
    if media_type is None:
        return None
    return path, media_type
