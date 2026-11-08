from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.authorization import require_verified_college
from app.core.errors import APIError
from app.models import College, Request, Resource, Transfer, User
from app.schemas.requests import RequestCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _begin_immediate(db: Session) -> None:
    # Authentication may have performed a SELECT in this request session. Under
    # SQLite's legacy transaction mode that does not start a DB transaction;
    # rollback the read transaction and acquire the write reservation explicitly.
    if db.in_transaction():
        db.rollback()
    db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _rollback_error(db: Session, status: int, code: str, message: str) -> None:
    db.rollback()
    raise APIError(status, code, message)


def _actor(db: Session, actor: User, *, verified: bool) -> User:
    current = db.get(User, actor.id)
    if current is None or not current.is_active or current.role != "college_representative" or current.college_id is None:
        raise APIError(403, "forbidden", "An active college representative is required.")
    if verified:
        require_verified_college(db, current.college_id)
    return current


def _get_request(db: Session, request_id: int) -> Request:
    request = db.scalar(
        select(Request).options(joinedload(Request.resource), joinedload(Request.requesting_college))
        .where(Request.id == request_id)
    )
    if request is None:
        raise APIError(404, "not_found", "Request not found.")
    return request


def _owner_college(db: Session, resource: Resource) -> College:
    college = db.get(College, resource.college_id)
    if college is None or college.verification_status != "verified":
        raise APIError(409, "ineligible_college", "The resource-owning college is not eligible to transact.")
    return college


def _validate_resource(db: Session, resource_id: int, expected_type: str, *, college_id: int | None = None) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise APIError(404, "resource_not_found", "Resource not found.")
    if resource.status != "active" or resource.transfer_type != expected_type:
        raise APIError(409, "resource_unavailable", "The resource is not active for this request type.")
    if college_id is not None and resource.college_id != college_id:
        raise APIError(403, "forbidden", "The offered resource must belong to your college.")
    if resource.quantity_available <= 0:
        raise APIError(409, "insufficient_stock", "The resource has no available inventory.")
    _owner_college(db, resource)
    return resource


def _reserve(db: Session, resource_id: int, quantity: int) -> bool:
    result = db.execute(
        update(Resource)
        .where(Resource.id == resource_id, Resource.status == "active", Resource.quantity_available >= quantity)
        .values(
            quantity_available=Resource.quantity_available - quantity,
            quantity_reserved=Resource.quantity_reserved + quantity,
            updated_at=_now(),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _release(db: Session, resource_id: int, quantity: int) -> bool:
    result = db.execute(
        update(Resource)
        .where(Resource.id == resource_id, Resource.quantity_reserved >= quantity)
        .values(
            quantity_available=Resource.quantity_available + quantity,
            quantity_reserved=Resource.quantity_reserved - quantity,
            updated_at=_now(),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def create_request(db: Session, *, actor: User, payload: RequestCreate) -> Request:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        expected_type = {"donation": "donation", "exchange": "exchange", "purchase_enquiry": "sale"}[payload.request_type]
        target = _validate_resource(db, payload.resource_id, expected_type)
        if target.college_id == current.college_id:
            _rollback_error(db, 403, "forbidden", "A college cannot request its own resource.")
        if payload.requested_quantity > target.quantity_available:
            _rollback_error(db, 409, "insufficient_stock", "Requested quantity exceeds currently available stock.")
        offered = None
        if payload.request_type == "exchange":
            if payload.offered_resource_id is None or payload.offered_quantity is None:
                _rollback_error(db, 422, "validation_error", "Exchange requests require an offered resource and quantity.")
            offered = _validate_resource(db, payload.offered_resource_id, "exchange", college_id=current.college_id)
            if offered.id == target.id:
                _rollback_error(db, 422, "invalid_exchange", "A resource cannot be exchanged for itself.")
            if payload.offered_quantity > offered.quantity_available:
                _rollback_error(db, 409, "insufficient_stock", "Offered quantity exceeds currently available stock.")
        elif payload.offered_resource_id is not None or payload.offered_quantity is not None:
            _rollback_error(db, 422, "validation_error", "Only exchange requests may include an offered resource.")
        request = Request(
            resource_id=target.id, requesting_college_id=current.college_id,
            requested_by_user_id=current.id, offered_resource_id=offered.id if offered else None,
            requested_quantity=payload.requested_quantity,
            offered_quantity=payload.offered_quantity if offered else None,
            request_type=payload.request_type, purpose=payload.purpose.strip(),
            message=payload.message.strip() if payload.message else None, status="pending",
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def list_requests(db: Session, *, actor: User, kind: str, page: int, page_size: int) -> tuple[list[Request], int]:
    if actor.college_id is None or actor.role != "college_representative":
        raise APIError(403, "forbidden", "College representative access is required.")
    query = select(Request).options(joinedload(Request.resource)).order_by(Request.created_at.desc(), Request.id.desc())
    if kind == "mine":
        query = query.where(Request.requesting_college_id == actor.college_id)
    else:
        query = query.join(Resource, Request.resource_id == Resource.id).where(Resource.college_id == actor.college_id)
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    items = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique())
    return items, total


def get_request(db: Session, *, actor: User, request_id: int) -> Request:
    request = _get_request(db, request_id)
    if actor.role != "college_representative" or actor.college_id not in {
        request.requesting_college_id, request.resource.college_id,
    }:
        raise APIError(404, "not_found", "Request not found.")
    return request


def _owner_actor(db: Session, actor: User, request: Request) -> User:
    current = _actor(db, actor, verified=True)
    if request.resource.college_id != current.college_id:
        raise APIError(403, "forbidden", "Only the resource-owning college may review this request.")
    if request.requesting_college_id == current.college_id:
        raise APIError(403, "forbidden", "The requesting college cannot review its own request.")
    return current


def approve_request(db: Session, *, actor: User, request_id: int, approved_quantity: int | None) -> Request:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        request = _get_request(db, request_id)
        _owner_actor(db, current, request)
        if request.status != "pending" or request.cancellation_requested_at is not None:
            _rollback_error(db, 409, "invalid_request_state", "Only a pending request can be approved.")
        quantity = approved_quantity if approved_quantity is not None else request.requested_quantity
        if request.request_type != "donation" and quantity != request.requested_quantity:
            _rollback_error(db, 422, "invalid_approval_quantity", "Exchange and purchase requests require full approval.")
        if quantity <= 0 or quantity > request.requested_quantity:
            _rollback_error(db, 422, "invalid_approval_quantity", "Approved quantity must be positive and no greater than requested quantity.")
        expected_type = {"donation": "donation", "exchange": "exchange", "purchase_enquiry": "sale"}[request.request_type]
        if request.resource.status != "active" or request.resource.transfer_type != expected_type:
            _rollback_error(db, 409, "resource_unavailable", "The requested resource is no longer active for this request type.")
        if request.request_type in {"donation", "exchange"}:
            if not _reserve(db, request.resource_id, quantity):
                _rollback_error(db, 409, "insufficient_stock", "The requested resource no longer has sufficient stock.")
            if request.request_type == "exchange" and not _reserve(db, request.offered_resource_id, request.offered_quantity):
                _rollback_error(db, 409, "insufficient_stock", "The offered resource no longer has sufficient stock.")
            if request.request_type == "exchange":
                offered_resource = db.get(Resource, request.offered_resource_id)
                if offered_resource is None or offered_resource.status != "active" or offered_resource.transfer_type != "exchange":
                    _rollback_error(db, 409, "resource_unavailable", "The offered resource is no longer active for exchange.")
        request.approved_quantity = quantity
        request.status = "approved"
        request.reviewed_by_user_id = current.id
        request.reviewed_at = _now()
        request.updated_at = _now()
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def reject_request(db: Session, *, actor: User, request_id: int, reason: str) -> Request:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        request = _get_request(db, request_id)
        _owner_actor(db, current, request)
        if request.status != "pending" or request.cancellation_requested_at is not None:
            _rollback_error(db, 409, "invalid_request_state", "Only a pending request can be rejected.")
        request.status = "rejected"
        request.rejection_reason = reason.strip()
        request.reviewed_by_user_id = current.id
        request.reviewed_at = _now()
        request.updated_at = _now()
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def confirm_purchase(db: Session, *, actor: User, request_id: int) -> tuple[Request, bool]:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        request = _get_request(db, request_id)
        if current.college_id != request.requesting_college_id:
            _rollback_error(db, 403, "forbidden", "Only the requesting college may confirm purchase intent.")
        if request.request_type != "purchase_enquiry" or request.status != "approved":
            _rollback_error(db, 409, "invalid_request_state", "Only approved purchase enquiries can be confirmed.")
        if request.purchase_intent_confirmed_at is not None:
            _rollback_error(db, 409, "already_confirmed", "Purchase intent has already been confirmed.")
        resource = db.get(Resource, request.resource_id)
        if resource is None or resource.status != "active" or resource.transfer_type != "sale":
            _rollback_error(db, 409, "resource_unavailable", "The requested resource is no longer active for sale.")
        quantity = request.approved_quantity or request.requested_quantity
        request.purchase_intent_confirmed_at = _now()
        request.purchase_confirmed_by_user_id = current.id
        request.updated_at = _now()
        success = _reserve(db, request.resource_id, quantity)
        if success:
            request.status = "in_progress"
        else:
            request.status = "awaiting_resolution"
        db.commit()
        db.refresh(request)
        return request, not success
    except Exception:
        db.rollback()
        raise


def submit_cancellation(db: Session, *, actor: User, request_id: int, reason: str) -> Request:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        request = _get_request(db, request_id)
        if request.requesting_college_id != current.college_id:
            _rollback_error(db, 403, "forbidden", "Only the requesting college may request cancellation.")
        if request.status in {"rejected", "completed", "cancelled"}:
            _rollback_error(db, 409, "invalid_request_state", "This request cannot be cancelled.")
        if request.cancellation_requested_at is not None:
            _rollback_error(db, 409, "cancellation_already_requested", "A cancellation request has already been submitted.")
        if db.scalar(select(func.count()).select_from(Transfer).where(Transfer.request_id == request.id)):
            _rollback_error(db, 409, "transfers_exist", "Request-level cancellation is unavailable after transfer batches exist.")
        request.cancellation_requested_by_user_id = current.id
        request.cancellation_requested_at = _now()
        request.cancellation_reason = reason.strip()
        request.cancellation_previous_status = request.status
        request.updated_at = _now()
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise


def decide_cancellation(db: Session, *, actor: User, request_id: int, decision: str) -> Request:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        request = _get_request(db, request_id)
        _owner_actor(db, current, request)
        if request.cancellation_requested_at is None or request.cancellation_decision is not None:
            _rollback_error(db, 409, "invalid_cancellation_state", "There is no pending cancellation to review.")
        if db.scalar(select(func.count()).select_from(Transfer).where(Transfer.request_id == request.id)):
            _rollback_error(db, 409, "transfers_exist", "Request-level cancellation is unavailable after transfer batches exist.")
        if decision == "approved":
            if request.request_type in {"donation", "exchange"} and request.approved_quantity:
                if not _release(db, request.resource_id, request.approved_quantity):
                    _rollback_error(db, 409, "inventory_conflict", "Reserved inventory could not be released safely.")
            if request.request_type == "exchange" and request.approved_quantity and request.offered_resource_id:
                if not _release(db, request.offered_resource_id, request.offered_quantity):
                    _rollback_error(db, 409, "inventory_conflict", "Offered inventory could not be released safely.")
            if request.request_type == "purchase_enquiry" and request.status == "in_progress" and request.approved_quantity:
                if not _release(db, request.resource_id, request.approved_quantity):
                    _rollback_error(db, 409, "inventory_conflict", "Reserved inventory could not be released safely.")
            request.status = "cancelled"
        else:
            request.status = request.cancellation_previous_status
        request.cancellation_decision = decision
        request.cancellation_reviewed_by_user_id = current.id
        request.cancellation_reviewed_at = _now()
        request.updated_at = _now()
        db.commit()
        db.refresh(request)
        return request
    except Exception:
        db.rollback()
        raise
