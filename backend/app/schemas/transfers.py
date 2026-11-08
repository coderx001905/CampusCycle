from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TransferCreate(InputModel):
    transfer_leg: Literal["requested_resource", "offered_resource"] = "requested_resource"
    quantity: int = Field(gt=0)
    pickup_or_delivery_date: datetime | None = None
    dispatch_notes: Annotated[str, StringConstraints(max_length=5000)] | None = None
    replacement_for_transfer_id: int | None = Field(default=None, gt=0)


class TransferDispatch(InputModel):
    dispatch_notes: Annotated[str, StringConstraints(max_length=5000)] | None = None
    pickup_or_delivery_date: datetime | None = None


class TransferReceipt(InputModel):
    quantity_received_good: int = Field(ge=0)
    quantity_damaged: int = Field(default=0, ge=0)
    quantity_missing: int = Field(default=0, ge=0)
    receipt_confirmation: Annotated[str, StringConstraints(max_length=5000)] | None = None


class TransferDisputeResolution(InputModel):
    dispute_outcome: Literal["accept_report", "replacement_approved", "claim_rejected"]
    dispute_resolution: Annotated[NonEmpty, StringConstraints(max_length=5000)]


class TransferCancellationRequest(InputModel):
    reason: Reason


class TransferCancellationDecision(InputModel):
    decision: Literal["approved", "rejected"]


class TransferStatusHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transfer_id: int
    changed_by_user_id: int | None
    actor_type: str
    previous_status: str | None
    new_status: str
    notes: str | None
    changed_at: datetime


class TransferItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    resource_id: int
    transfer_leg: str
    source_college_id: int
    destination_college_id: int
    quantity: int
    quantity_received_good: int | None
    quantity_damaged: int | None
    quantity_missing: int | None
    dispute_status: str
    dispute_resolution: str | None
    dispute_outcome: str | None
    replacement_for_transfer_id: int | None
    dispute_resolved_by_user_id: int | None
    dispute_resolved_at: datetime | None
    created_by_user_id: int
    dispatched_by_user_id: int | None
    received_by_user_id: int | None
    pickup_or_delivery_date: datetime | None
    status: str
    dispatch_notes: str | None
    receipt_confirmation: str | None
    received_at: datetime | None
    cancellation_requested_by_user_id: int | None
    cancellation_requested_at: datetime | None
    cancellation_reason: str | None
    cancellation_reviewed_by_user_id: int | None
    cancellation_reviewed_at: datetime | None
    cancellation_decision: str | None
    created_at: datetime
    completed_at: datetime | None
