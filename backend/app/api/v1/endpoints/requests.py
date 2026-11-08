from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import require_college_representative
from app.core.errors import APIError
from app.db.session import get_db
from app.models import User
from app.schemas.requests import (
    CancellationDecision,
    CancellationSubmission,
    RequestApproval,
    RequestCreate,
    RequestItem,
    RequestRejection,
)
from app.services.requests import (
    approve_request,
    confirm_purchase,
    create_request,
    decide_cancellation,
    get_request,
    list_requests,
    reject_request,
    submit_cancellation,
)

router = APIRouter(tags=["requests"])


def _item(request) -> dict:
    return RequestItem.model_validate(request).model_dump(mode="json")


@router.post("/requests", status_code=201)
def submit_request(payload: RequestCreate,
                   user: User = Depends(require_college_representative),
                   db: Session = Depends(get_db)) -> dict:
    request = create_request(db, actor=user, payload=payload)
    return {"success": True, "data": _item(request)}


@router.get("/requests/mine")
def list_mine(page: int = Query(default=1, ge=1),
              page_size: int = Query(default=20, ge=1, le=100),
              user: User = Depends(require_college_representative),
              db: Session = Depends(get_db)) -> dict:
    items, total = list_requests(db, actor=user, kind="mine", page=page, page_size=page_size)
    return {"success": True, "data": {"items": [_item(item) for item in items], "page": page,
                                       "page_size": page_size, "total": total}}


@router.get("/requests/received")
def list_received(page: int = Query(default=1, ge=1),
                  page_size: int = Query(default=20, ge=1, le=100),
                  user: User = Depends(require_college_representative),
                  db: Session = Depends(get_db)) -> dict:
    items, total = list_requests(db, actor=user, kind="received", page=page, page_size=page_size)
    return {"success": True, "data": {"items": [_item(item) for item in items], "page": page,
                                       "page_size": page_size, "total": total}}


@router.post("/requests/{request_id}/approve")
def approve(request_id: int, payload: RequestApproval | None = None,
            user: User = Depends(require_college_representative),
            db: Session = Depends(get_db)) -> dict:
    request = approve_request(db, actor=user, request_id=request_id,
                              approved_quantity=payload.approved_quantity if payload else None)
    return {"success": True, "data": _item(request)}


@router.post("/requests/{request_id}/reject")
def reject(request_id: int, payload: RequestRejection,
           user: User = Depends(require_college_representative),
           db: Session = Depends(get_db)) -> dict:
    request = reject_request(db, actor=user, request_id=request_id, reason=payload.reason)
    return {"success": True, "data": _item(request)}


@router.post("/requests/{request_id}/purchase-confirmation")
def purchase_confirmation(request_id: int,
                          user: User = Depends(require_college_representative),
                          db: Session = Depends(get_db)) -> dict:
    request, insufficient = confirm_purchase(db, actor=user, request_id=request_id)
    if insufficient:
        raise APIError(409, "insufficient_stock", "The seller no longer has sufficient stock; the request awaits resolution.")
    return {"success": True, "data": _item(request)}


@router.post("/requests/{request_id}/cancel")
def cancel_request(request_id: int, payload: CancellationSubmission,
                   user: User = Depends(require_college_representative),
                   db: Session = Depends(get_db)) -> dict:
    request = submit_cancellation(db, actor=user, request_id=request_id, reason=payload.reason)
    return {"success": True, "data": _item(request)}


@router.post("/requests/{request_id}/cancellation-decision")
def cancellation_decision(request_id: int, payload: CancellationDecision,
                          user: User = Depends(require_college_representative),
                          db: Session = Depends(get_db)) -> dict:
    request = decide_cancellation(db, actor=user, request_id=request_id, decision=payload.decision)
    return {"success": True, "data": _item(request)}


@router.get("/requests/{request_id}")
def request_details(request_id: int,
                    user: User = Depends(require_college_representative),
                    db: Session = Depends(get_db)) -> dict:
    request = get_request(db, actor=user, request_id=request_id)
    return {"success": True, "data": _item(request)}
