from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import (
    get_current_user,
    require_college_representative,
)
from app.db.session import get_db
from app.models import User
from app.schemas.transfers import (
    TransferCancellationDecision,
    TransferCancellationRequest,
    TransferCreate,
    TransferDispatch,
    TransferDisputeResolution,
    TransferItem,
    TransferReceipt,
    TransferStatusHistoryItem,
)
from app.services.transfers import (
    confirm_receipt,
    create_transfer,
    decide_cancellation,
    dispatch_transfer,
    get_transfer,
    get_transfer_history,
    list_transfers,
    request_cancellation,
    resolve_dispute,
)

router = APIRouter(tags=["transfers"])


def _item(transfer) -> dict:
    return TransferItem.model_validate(transfer).model_dump(mode="json")


def _history_item(history) -> dict:
    return TransferStatusHistoryItem.model_validate(history).model_dump(mode="json")


@router.post("/requests/{request_id}/transfers", status_code=201)
def create_batch(
    request_id: int,
    payload: TransferCreate,
    user: User = Depends(require_college_representative),
    db: Session = Depends(get_db),
) -> dict:
    transfer = create_transfer(db, actor=user, request_id=request_id, payload=payload)
    return {"success": True, "data": _item(transfer)}


@router.get("/transfers")
def get_transfers(
    request_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    transfer_leg: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = list_transfers(
        db,
        actor=user,
        request_id=request_id,
        status=status,
        transfer_leg=transfer_leg,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "data": {
            "items": [_item(item) for item in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }


@router.get("/transfers/{transfer_id}")
def get_single_transfer(
    transfer_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    transfer = get_transfer(db, actor=user, transfer_id=transfer_id)
    return {"success": True, "data": _item(transfer)}


@router.get("/transfers/{transfer_id}/history")
def get_history(
    transfer_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    history = get_transfer_history(db, actor=user, transfer_id=transfer_id)
    return {
        "success": True,
        "data": {
            "items": [_history_item(item) for item in history],
            "total": len(history),
        },
    }


@router.post("/transfers/{transfer_id}/dispatch")
def dispatch(
    transfer_id: int,
    payload: TransferDispatch | None = None,
    user: User = Depends(require_college_representative),
    db: Session = Depends(get_db),
) -> dict:
    transfer = dispatch_transfer(
        db,
        actor=user,
        transfer_id=transfer_id,
        payload=payload or TransferDispatch(),
    )
    return {"success": True, "data": _item(transfer)}


@router.post("/transfers/{transfer_id}/receipt")
def receipt(
    transfer_id: int,
    payload: TransferReceipt,
    user: User = Depends(require_college_representative),
    db: Session = Depends(get_db),
) -> dict:
    transfer = confirm_receipt(db, actor=user, transfer_id=transfer_id, payload=payload)
    return {"success": True, "data": _item(transfer)}


@router.post("/transfers/{transfer_id}/cancel")
def cancel(
    transfer_id: int,
    payload: TransferCancellationRequest,
    user: User = Depends(require_college_representative),
    db: Session = Depends(get_db),
) -> dict:
    transfer = request_cancellation(db, actor=user, transfer_id=transfer_id, payload=payload)
    return {"success": True, "data": _item(transfer)}


@router.post("/transfers/{transfer_id}/cancellation-decision")
def cancellation_decision(
    transfer_id: int,
    payload: TransferCancellationDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    transfer = decide_cancellation(db, actor=user, transfer_id=transfer_id, payload=payload)
    return {"success": True, "data": _item(transfer)}


@router.post("/transfers/{transfer_id}/dispute-resolution")
def dispute_resolution(
    transfer_id: int,
    payload: TransferDisputeResolution,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    transfer = resolve_dispute(db, actor=user, transfer_id=transfer_id, payload=payload)
    return {"success": True, "data": _item(transfer)}
