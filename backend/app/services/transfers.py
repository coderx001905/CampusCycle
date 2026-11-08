from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.authorization import require_verified_college
from app.core.errors import APIError
from app.models import Request, Resource, Transfer, TransferStatusHistory, User
from app.schemas.transfers import (
    TransferCancellationDecision,
    TransferCancellationRequest,
    TransferCreate,
    TransferDispatch,
    TransferDisputeResolution,
    TransferReceipt,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _begin_immediate(db: Session) -> None:
    if db.in_transaction():
        db.rollback()
    db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _rollback_error(db: Session, status: int, code: str, message: str) -> None:
    db.rollback()
    raise APIError(status, code, message)


def _actor(db: Session, actor: User, *, verified: bool = True) -> User:
    current = db.get(User, actor.id)
    if current is None or not current.is_active:
        raise APIError(403, "forbidden", "An active authenticated user is required.")
    if current.role == "platform_admin":
        return current
    if current.role == "college_representative" and current.college_id is not None:
        if verified:
            require_verified_college(db, current.college_id)
        return current
    raise APIError(403, "forbidden", "Active college representative or platform administrator is required.")


def _get_request(db: Session, request_id: int) -> Request:
    request = db.scalar(
        select(Request)
        .options(joinedload(Request.resource), joinedload(Request.requesting_college))
        .where(Request.id == request_id)
    )
    if request is None:
        raise APIError(404, "not_found", "Request not found.")
    return request


def _get_transfer(db: Session, transfer_id: int) -> Transfer:
    transfer = db.scalar(
        select(Transfer)
        .options(
            joinedload(Transfer.request).joinedload(Request.resource),
            joinedload(Transfer.resource),
        )
        .where(Transfer.id == transfer_id)
    )
    if transfer is None:
        raise APIError(404, "not_found", "Transfer not found.")
    return transfer


def _reserve(db: Session, resource_id: int, quantity: int) -> bool:
    if quantity <= 0:
        return True
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
    if quantity <= 0:
        return True
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


def _deduct_delivered(db: Session, resource_id: int, quantity: int) -> bool:
    if quantity <= 0:
        return True
    result = db.execute(
        update(Resource)
        .where(
            Resource.id == resource_id,
            Resource.quantity_reserved >= quantity,
            Resource.quantity_total >= quantity,
        )
        .values(
            quantity_total=Resource.quantity_total - quantity,
            quantity_reserved=Resource.quantity_reserved - quantity,
            updated_at=_now(),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def create_transfer(
    db: Session, *, actor: User, request_id: int, payload: TransferCreate
) -> Transfer:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        request = _get_request(db, request_id)

        if request.status not in ("approved", "in_progress"):
            _rollback_error(
                db,
                409,
                "invalid_request_state",
                f"Transfers can only be created for approved or in-progress requests, not '{request.status}'.",
            )
        if request.request_type == "purchase_enquiry" and request.purchase_intent_confirmed_at is None:
            _rollback_error(
                db,
                409,
                "invalid_request_state",
                "Purchase intent must be confirmed before creating transfers.",
            )

        if payload.transfer_leg == "requested_resource":
            source_college_id = request.resource.college_id
            destination_college_id = request.requesting_college_id
            resource_id = request.resource_id
            approved_limit = request.approved_quantity or request.requested_quantity
        elif payload.transfer_leg == "offered_resource":
            if request.request_type != "exchange":
                _rollback_error(
                    db,
                    422,
                    "invalid_transfer_leg",
                    "Offered resource leg is only applicable to exchange requests.",
                )
            if not request.offered_resource_id or not request.offered_quantity:
                _rollback_error(
                    db,
                    422,
                    "invalid_transfer_leg",
                    "Exchange request is missing offered resource details.",
                )
            source_college_id = request.requesting_college_id
            destination_college_id = request.resource.college_id
            resource_id = request.offered_resource_id
            approved_limit = request.offered_quantity
        else:
            _rollback_error(
                db,
                422,
                "invalid_transfer_leg",
                f"Invalid transfer leg '{payload.transfer_leg}'.",
            )

        if current.role != "college_representative" or current.college_id != source_college_id:
            _rollback_error(
                db,
                403,
                "forbidden",
                "Only the source college representative can create this transfer batch.",
            )

        require_verified_college(db, destination_college_id)

        if payload.replacement_for_transfer_id is not None:
            orig = db.get(Transfer, payload.replacement_for_transfer_id)
            if orig is None or orig.request_id != request.id:
                _rollback_error(
                    db,
                    404,
                    "not_found",
                    "The original transfer referenced for replacement was not found in this request.",
                )
            if orig.transfer_leg != payload.transfer_leg:
                _rollback_error(
                    db,
                    422,
                    "invalid_replacement_leg",
                    "Replacement transfer leg must match the original transfer leg.",
                )
            if orig.dispute_outcome != "replacement_approved":
                _rollback_error(
                    db,
                    409,
                    "invalid_replacement_target",
                    "A replacement transfer can only be created for a transfer with dispute outcome 'replacement_approved'.",
                )
            orig_disputed_qty = (orig.quantity_damaged or 0) + (orig.quantity_missing or 0)
            existing_repl_qty = (
                db.scalar(
                    select(func.coalesce(func.sum(Transfer.quantity), 0)).where(
                        Transfer.replacement_for_transfer_id == orig.id,
                        Transfer.status != "cancelled",
                    )
                )
                or 0
            )
            if existing_repl_qty + payload.quantity > orig_disputed_qty:
                _rollback_error(
                    db,
                    409,
                    "quantity_exceeds_disputed",
                    f"Replacement quantity ({existing_repl_qty + payload.quantity}) exceeds disputed quantity ({orig_disputed_qty}).",
                )
            if not _reserve(db, resource_id, payload.quantity):
                _rollback_error(
                    db,
                    409,
                    "insufficient_stock",
                    "Insufficient available stock to reserve replacement items.",
                )
        else:
            existing_qty = (
                db.scalar(
                    select(func.coalesce(func.sum(Transfer.quantity), 0)).where(
                        Transfer.request_id == request.id,
                        Transfer.transfer_leg == payload.transfer_leg,
                        Transfer.status != "cancelled",
                        Transfer.replacement_for_transfer_id.is_(None),
                    )
                )
                or 0
            )
            if existing_qty + payload.quantity > approved_limit:
                _rollback_error(
                    db,
                    409,
                    "quantity_exceeds_approved",
                    f"Aggregate transfer quantity ({existing_qty + payload.quantity}) would exceed the approved limit ({approved_limit}) for this leg.",
                )

        now = _now()
        transfer = Transfer(
            request_id=request.id,
            resource_id=resource_id,
            transfer_leg=payload.transfer_leg,
            source_college_id=source_college_id,
            destination_college_id=destination_college_id,
            quantity=payload.quantity,
            pickup_or_delivery_date=payload.pickup_or_delivery_date,
            dispatch_notes=payload.dispatch_notes,
            replacement_for_transfer_id=payload.replacement_for_transfer_id,
            created_by_user_id=current.id,
            status="preparing",
            dispute_status="none",
            created_at=now,
        )
        db.add(transfer)
        db.flush()

        if request.status == "approved":
            request.status = "in_progress"
            request.updated_at = now

        history = TransferStatusHistory(
            transfer_id=transfer.id,
            changed_by_user_id=current.id,
            actor_type="user",
            previous_status=None,
            new_status="preparing",
            notes=payload.dispatch_notes or "Transfer batch created.",
            changed_at=now,
        )
        db.add(history)
        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise


def get_transfer(db: Session, *, actor: User, transfer_id: int) -> Transfer:
    transfer = _get_transfer(db, transfer_id)
    if actor.role == "platform_admin":
        return transfer
    if actor.role == "college_representative" and actor.college_id in (
        transfer.source_college_id,
        transfer.destination_college_id,
    ):
        return transfer
    raise APIError(404, "not_found", "Transfer not found.")


def list_transfers(
    db: Session,
    *,
    actor: User,
    request_id: int | None = None,
    status: str | None = None,
    transfer_leg: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Transfer], int]:
    query = select(Transfer).order_by(Transfer.created_at.desc(), Transfer.id.desc())

    if actor.role == "platform_admin":
        pass
    elif actor.role == "college_representative" and actor.college_id is not None:
        require_verified_college(db, actor.college_id)
        query = query.where(
            or_(
                Transfer.source_college_id == actor.college_id,
                Transfer.destination_college_id == actor.college_id,
            )
        )
    else:
        raise APIError(403, "forbidden", "Unauthorized to view transfers.")

    if request_id is not None:
        query = query.where(Transfer.request_id == request_id)
    if status is not None:
        query = query.where(Transfer.status == status)
    if transfer_leg is not None:
        query = query.where(Transfer.transfer_leg == transfer_leg)

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    items = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def get_transfer_history(
    db: Session, *, actor: User, transfer_id: int
) -> list[TransferStatusHistory]:
    transfer = get_transfer(db, actor=actor, transfer_id=transfer_id)
    history = list(
        db.scalars(
            select(TransferStatusHistory)
            .where(TransferStatusHistory.transfer_id == transfer.id)
            .order_by(TransferStatusHistory.changed_at.asc(), TransferStatusHistory.id.asc())
        ).all()
    )
    return history


def dispatch_transfer(
    db: Session, *, actor: User, transfer_id: int, payload: TransferDispatch
) -> Transfer:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        transfer = _get_transfer(db, transfer_id)

        if current.role != "college_representative" or current.college_id != transfer.source_college_id:
            _rollback_error(
                db,
                403,
                "forbidden",
                "Only the source college representative can dispatch this transfer.",
            )

        if transfer.status != "preparing":
            _rollback_error(
                db,
                409,
                "invalid_transfer_state",
                f"Only preparing transfers can be dispatched; current status is '{transfer.status}'.",
            )

        now = _now()
        transfer.status = "dispatched"
        transfer.dispatched_by_user_id = current.id
        if payload.dispatch_notes:
            transfer.dispatch_notes = payload.dispatch_notes
        if payload.pickup_or_delivery_date:
            transfer.pickup_or_delivery_date = payload.pickup_or_delivery_date

        history = TransferStatusHistory(
            transfer_id=transfer.id,
            changed_by_user_id=current.id,
            actor_type="user",
            previous_status="preparing",
            new_status="dispatched",
            notes=payload.dispatch_notes or "Transfer batch dispatched.",
            changed_at=now,
        )
        db.add(history)
        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise


def confirm_receipt(
    db: Session, *, actor: User, transfer_id: int, payload: TransferReceipt
) -> Transfer:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        transfer = _get_transfer(db, transfer_id)

        if current.role != "college_representative" or current.college_id != transfer.destination_college_id:
            _rollback_error(
                db,
                403,
                "forbidden",
                "Only the destination college representative can confirm receipt.",
            )

        if transfer.status != "dispatched":
            _rollback_error(
                db,
                409,
                "invalid_transfer_state",
                f"Only dispatched transfers can be confirmed for receipt; current status is '{transfer.status}'.",
            )

        good = payload.quantity_received_good
        damaged = payload.quantity_damaged
        missing = payload.quantity_missing

        if good + damaged + missing != transfer.quantity:
            _rollback_error(
                db,
                422,
                "invalid_receipt_quantities",
                f"The sum of good ({good}), damaged ({damaged}), and missing ({missing}) quantities must equal the transfer quantity ({transfer.quantity}).",
            )

        now = _now()
        transfer.quantity_received_good = good
        transfer.quantity_damaged = damaged
        transfer.quantity_missing = missing
        transfer.received_by_user_id = current.id
        transfer.received_at = now
        transfer.receipt_confirmation = payload.receipt_confirmation

        if good > 0:
            if not _deduct_delivered(db, transfer.resource_id, good):
                _rollback_error(
                    db,
                    409,
                    "inventory_conflict",
                    "Could not safely deduct delivered good quantity from reserved stock.",
                )

        if transfer.replacement_for_transfer_id is not None and good > 0:
            orig = db.get(Transfer, transfer.replacement_for_transfer_id)
            if orig is not None:
                if not _deduct_delivered(db, orig.resource_id, good):
                    _rollback_error(
                        db,
                        409,
                        "inventory_conflict",
                        "Could not safely write off original disputed quantity.",
                    )

        if damaged > 0 or missing > 0:
            transfer.status = "disputed"
            transfer.dispute_status = "open"
            history = TransferStatusHistory(
                transfer_id=transfer.id,
                changed_by_user_id=current.id,
                actor_type="user",
                previous_status="dispatched",
                new_status="disputed",
                notes=payload.receipt_confirmation or "Receipt confirmed with disputes.",
                changed_at=now,
            )
        else:
            transfer.status = "completed"
            transfer.completed_at = now
            history = TransferStatusHistory(
                transfer_id=transfer.id,
                changed_by_user_id=current.id,
                actor_type="user",
                previous_status="dispatched",
                new_status="completed",
                notes=payload.receipt_confirmation or "All items received in good condition.",
                changed_at=now,
            )

        db.add(history)
        _check_and_update_request_completion(db, transfer.request_id)
        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise


def resolve_dispute(
    db: Session, *, actor: User, transfer_id: int, payload: TransferDisputeResolution
) -> Transfer:
    _begin_immediate(db)
    try:
        if actor.role != "platform_admin":
            _rollback_error(
                db,
                403,
                "forbidden",
                "Only a platform administrator can resolve transfer disputes.",
            )
        current = db.get(User, actor.id)
        if current is None or not current.is_active:
            _rollback_error(db, 403, "forbidden", "Active platform administrator required.")

        transfer = _get_transfer(db, transfer_id)
        if transfer.status != "disputed" or transfer.dispute_status != "open":
            _rollback_error(
                db,
                409,
                "invalid_dispute_state",
                "Only transfers with an open dispute can be resolved.",
            )

        now = _now()
        disputed_qty = (transfer.quantity_damaged or 0) + (transfer.quantity_missing or 0)

        if payload.dispute_outcome == "accept_report":
            # Only verified good quantities were deducted at receipt.
            # Damaged and missing quantities remain reserved; they are NOT automatically written off.
            transfer.status = "completed"
            transfer.completed_at = now
        elif payload.dispute_outcome == "replacement_approved":
            # Disputed quantity remains reserved until replacement receipt is verified.
            transfer.status = "completed"
            transfer.completed_at = now
        elif payload.dispute_outcome == "claim_rejected":
            # Disputed quantity remains reserved for manual accounting; do not release or write off.
            transfer.status = "completed"
            transfer.completed_at = now

        transfer.dispute_status = "resolved"
        transfer.dispute_outcome = payload.dispute_outcome
        transfer.dispute_resolution = payload.dispute_resolution
        transfer.dispute_resolved_by_user_id = current.id
        transfer.dispute_resolved_at = now

        history = TransferStatusHistory(
            transfer_id=transfer.id,
            changed_by_user_id=current.id,
            actor_type="user",
            previous_status="disputed",
            new_status=transfer.status,
            notes=f"Dispute resolved ({payload.dispute_outcome}): {payload.dispute_resolution}",
            changed_at=now,
        )
        db.add(history)
        _check_and_update_request_completion(db, transfer.request_id)
        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise


def request_cancellation(
    db: Session, *, actor: User, transfer_id: int, payload: TransferCancellationRequest
) -> Transfer:
    _begin_immediate(db)
    try:
        current = _actor(db, actor, verified=True)
        transfer = _get_transfer(db, transfer_id)

        if current.role != "college_representative" or current.college_id not in (
            transfer.source_college_id,
            transfer.destination_college_id,
        ):
            _rollback_error(
                db,
                403,
                "forbidden",
                "Only participating college representatives can request cancellation.",
            )

        if transfer.status == "cancellation_pending":
            _rollback_error(
                db,
                409,
                "cancellation_already_requested",
                "A cancellation request is already pending for this transfer.",
            )

        if transfer.status not in ("preparing", "dispatched"):
            _rollback_error(
                db,
                409,
                "invalid_transfer_state",
                f"Transfers in status '{transfer.status}' cannot be cancelled.",
            )

        now = _now()
        prev_status = transfer.status
        transfer.status = "cancellation_pending"
        transfer.cancellation_requested_by_user_id = current.id
        transfer.cancellation_requested_at = now
        transfer.cancellation_reason = payload.reason

        history = TransferStatusHistory(
            transfer_id=transfer.id,
            changed_by_user_id=current.id,
            actor_type="user",
            previous_status=prev_status,
            new_status="cancellation_pending",
            notes=payload.reason,
            changed_at=now,
        )
        db.add(history)
        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise


def decide_cancellation(
    db: Session, *, actor: User, transfer_id: int, payload: TransferCancellationDecision
) -> Transfer:
    _begin_immediate(db)
    try:
        transfer = _get_transfer(db, transfer_id)
        if transfer.status != "cancellation_pending":
            _rollback_error(
                db,
                409,
                "invalid_cancellation_state",
                "There is no pending cancellation request for this transfer.",
            )

        any_dispatched = (
            db.scalar(
                select(func.count())
                .select_from(Transfer)
                .where(
                    Transfer.request_id == transfer.request_id,
                    Transfer.dispatched_by_user_id.is_not(None),
                )
            )
            > 0
        )

        if not any_dispatched:
            if (
                actor.role != "college_representative"
                or actor.college_id != transfer.request.resource.college_id
            ):
                _rollback_error(
                    db,
                    403,
                    "forbidden",
                    "Before any dispatch has occurred, only the resource-owning college representative can decide on cancellation.",
                )
            current = _actor(db, actor, verified=True)
        else:
            if actor.role != "platform_admin":
                _rollback_error(
                    db,
                    403,
                    "forbidden",
                    "After dispatch has occurred, only a platform administrator can decide on cancellation.",
                )
            current = db.get(User, actor.id)
            if current is None or not current.is_active:
                _rollback_error(db, 403, "forbidden", "Active platform administrator required.")

        now = _now()
        if payload.decision == "approved":
            if transfer.dispatched_by_user_id is not None:
                _rollback_error(
                    db,
                    409,
                    "cannot_cancel_dispatched",
                    "Dispatched batches cannot be cancelled. They must continue through receipt and dispute resolution.",
                )
            if not _release(db, transfer.resource_id, transfer.quantity):
                _rollback_error(
                    db,
                    409,
                    "inventory_conflict",
                    "Reserved inventory could not be released safely.",
                )
            transfer.status = "cancelled"
            transfer.cancellation_decision = "approved"
            transfer.cancellation_reviewed_by_user_id = current.id
            transfer.cancellation_reviewed_at = now

            history = TransferStatusHistory(
                transfer_id=transfer.id,
                changed_by_user_id=current.id,
                actor_type="user",
                previous_status="cancellation_pending",
                new_status="cancelled",
                notes="Cancellation approved. Reserved inventory released.",
                changed_at=now,
            )
            db.add(history)
        else:
            restored_status = "dispatched" if transfer.dispatched_by_user_id is not None else "preparing"
            transfer.status = restored_status
            transfer.cancellation_decision = "rejected"
            transfer.cancellation_reviewed_by_user_id = current.id
            transfer.cancellation_reviewed_at = now

            history = TransferStatusHistory(
                transfer_id=transfer.id,
                changed_by_user_id=current.id,
                actor_type="user",
                previous_status="cancellation_pending",
                new_status=restored_status,
                notes="Cancellation request rejected.",
                changed_at=now,
            )
            db.add(history)

        _check_and_update_request_completion(db, transfer.request_id)
        db.commit()
        db.refresh(transfer)
        return transfer
    except Exception:
        db.rollback()
        raise


def _check_and_update_request_completion(db: Session, request_id: int) -> None:
    request = db.get(Request, request_id)
    if request is None or request.status in ("completed", "rejected", "cancelled"):
        return

    legs = ["requested_resource"]
    targets = {
        "requested_resource": request.approved_quantity or request.requested_quantity
    }
    if request.request_type == "exchange":
        legs.append("offered_resource")
        targets["offered_resource"] = request.offered_quantity or 0

    all_transfers = list(db.scalars(select(Transfer).where(Transfer.request_id == request.id)))

    for leg in legs:
        leg_transfers = [t for t in all_transfers if t.transfer_leg == leg]
        if not leg_transfers:
            return

        for t in leg_transfers:
            if t.status in ("preparing", "dispatched", "cancellation_pending"):
                return
            if t.dispute_status == "open" or t.status == "disputed":
                return
            # If any transfer has disputed inventory that remains held in reserved
            # (i.e. accept_report or claim_rejected with damaged/missing items),
            # disputed inventory remains unaccounted for; request cannot complete.
            if t.dispute_outcome in ("accept_report", "claim_rejected"):
                disputed_count = (t.quantity_damaged or 0) + (t.quantity_missing or 0)
                if disputed_count > 0:
                    return
            if t.dispute_outcome == "replacement_approved":
                needed = (t.quantity_damaged or 0) + (t.quantity_missing or 0)
                replacements = [
                    r
                    for r in leg_transfers
                    if r.replacement_for_transfer_id == t.id and r.status != "cancelled"
                ]
                good_replacements = sum(
                    (r.quantity_received_good or 0)
                    for r in replacements
                    if r.status == "completed"
                )
                if good_replacements < needed:
                    return

        accounted = 0
        for t in leg_transfers:
            if t.status == "completed":
                accounted += t.quantity_received_good or 0

        if accounted < targets[leg]:
            return

    now = _now()
    request.status = "completed"
    request.updated_at = now
