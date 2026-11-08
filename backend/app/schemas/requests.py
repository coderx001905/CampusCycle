from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequestCreate(InputModel):
    resource_id: int = Field(gt=0)
    request_type: Literal["donation", "exchange", "purchase_enquiry"]
    requested_quantity: int = Field(gt=0)
    purpose: Annotated[NonEmpty, StringConstraints(max_length=5000)]
    message: Annotated[str, StringConstraints(max_length=5000)] | None = None
    offered_resource_id: int | None = Field(default=None, gt=0)
    offered_quantity: int | None = Field(default=None, gt=0)


class RequestApproval(InputModel):
    approved_quantity: int | None = Field(default=None, gt=0)


class RequestRejection(InputModel):
    reason: Reason


class CancellationSubmission(InputModel):
    reason: Reason


class CancellationDecision(InputModel):
    decision: Literal["approved", "rejected"]


class RequestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_id: int
    requesting_college_id: int
    requested_by_user_id: int
    offered_resource_id: int | None
    request_type: str
    requested_quantity: int
    offered_quantity: int | None
    approved_quantity: int | None
    purpose: str
    message: str | None
    rejection_reason: str | None
    status: str
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    purchase_intent_confirmed_at: datetime | None
    purchase_confirmed_by_user_id: int | None
    cancellation_requested_by_user_id: int | None
    cancellation_requested_at: datetime | None
    cancellation_reason: str | None
    cancellation_reviewed_by_user_id: int | None
    cancellation_reviewed_at: datetime | None
    cancellation_previous_status: str | None
    cancellation_decision: str | None
    created_at: datetime
    updated_at: datetime

