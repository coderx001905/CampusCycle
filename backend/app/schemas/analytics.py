from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Category Analytics ---
class CategoryMetricItem(SchemaModel):
    category: str
    total_listings: int = Field(ge=0)
    active_listings: int = Field(ge=0)
    total_quantity: int = Field(ge=0)
    available_quantity: int = Field(ge=0)
    reserved_quantity: int = Field(ge=0)


class CategoryAnalyticsData(SchemaModel):
    scope: Literal["global", "college"]
    college_id: int | None = None
    items: list[CategoryMetricItem]
    total_categories: int = Field(ge=0)


# --- Request Analytics ---
class RequestStatusCountItem(SchemaModel):
    status: str
    count: int = Field(ge=0)


class RequestTypeCountItem(SchemaModel):
    request_type: str
    count: int = Field(ge=0)
    quantity: int = Field(ge=0)


class RequestAnalyticsData(SchemaModel):
    scope: Literal["global", "college"]
    college_id: int | None = None
    total_requests: int = Field(ge=0)
    by_status: list[RequestStatusCountItem]
    by_type: list[RequestTypeCountItem]
    total_requested_quantity: int = Field(ge=0)
    total_approved_quantity: int = Field(ge=0)
    fulfillment_rate: float = Field(ge=0.0, le=100.0)
    sent_count: int | None = None
    received_count: int | None = None


# --- Transfer Analytics ---
class TransferStatusCountItem(SchemaModel):
    status: str
    count: int = Field(ge=0)
    quantity: int = Field(ge=0)


class TransferLegCountItem(SchemaModel):
    leg: str
    count: int = Field(ge=0)
    quantity: int = Field(ge=0)


class TransferDisputeMetrics(SchemaModel):
    total_disputed: int = Field(ge=0)
    open_disputes: int = Field(ge=0)
    resolved_disputes: int = Field(ge=0)
    outcomes: dict[str, int]


class TransferQuantityMetrics(SchemaModel):
    total_shipped: int = Field(ge=0)
    received_good: int = Field(ge=0)
    damaged: int = Field(ge=0)
    missing: int = Field(ge=0)


class TransferAnalyticsData(SchemaModel):
    scope: Literal["global", "college"]
    college_id: int | None = None
    total_transfers: int = Field(ge=0)
    by_status: list[TransferStatusCountItem]
    by_leg: list[TransferLegCountItem]
    dispute_metrics: TransferDisputeMetrics
    quantity_metrics: TransferQuantityMetrics
    outbound_count: int | None = None
    inbound_count: int | None = None


# --- College Analytics (Platform Admin only) ---
class TopParticipatingCollegeItem(SchemaModel):
    id: int
    name: str
    city: str
    verification_status: str
    active_listings_count: int = Field(ge=0)
    completed_transfers_count: int = Field(ge=0)


class CollegeAnalyticsData(SchemaModel):
    total_colleges: int = Field(ge=0)
    verified_colleges: int = Field(ge=0)
    pending_colleges: int = Field(ge=0)
    rejected_colleges: int = Field(ge=0)
    colleges_with_active_listings: int = Field(ge=0)
    colleges_with_completed_transfers: int = Field(ge=0)
    top_participating_colleges: list[TopParticipatingCollegeItem]


# --- Summary Analytics ---
class CollegeSummaryMetrics(SchemaModel):
    total_colleges: int = Field(ge=0)
    verified_colleges: int = Field(ge=0)
    pending_colleges: int = Field(ge=0)
    rejected_colleges: int = Field(ge=0)


class ResourceSummaryMetrics(SchemaModel):
    total_listings: int = Field(ge=0)
    active_listings: int = Field(ge=0)
    inactive_listings: int = Field(ge=0)
    depleted_listings: int = Field(ge=0)
    total_quantity: int = Field(ge=0)
    available_quantity: int = Field(ge=0)
    reserved_quantity: int = Field(ge=0)


class RequestSummaryMetrics(SchemaModel):
    total_requests: int = Field(ge=0)
    pending_requests: int = Field(ge=0)
    approved_requests: int = Field(ge=0)
    rejected_requests: int = Field(ge=0)
    in_progress_requests: int = Field(ge=0)
    awaiting_resolution_requests: int = Field(ge=0)
    completed_requests: int = Field(ge=0)
    cancelled_requests: int = Field(ge=0)
    incoming_requests: int | None = None
    outgoing_requests: int | None = None


class TransferSummaryMetrics(SchemaModel):
    total_transfers: int = Field(ge=0)
    preparing_transfers: int = Field(ge=0)
    dispatched_transfers: int = Field(ge=0)
    partially_received_transfers: int = Field(ge=0)
    disputed_transfers: int = Field(ge=0)
    received_transfers: int = Field(ge=0)
    completed_transfers: int = Field(ge=0)
    cancellation_pending_transfers: int = Field(ge=0)
    cancelled_transfers: int = Field(ge=0)
    outbound_transfers: int | None = None
    inbound_transfers: int | None = None


class AnalyticsSummaryData(SchemaModel):
    scope: Literal["global", "college"]
    college_id: int | None = None
    verification_status: str | None = None
    colleges: CollegeSummaryMetrics | None = None
    resources: ResourceSummaryMetrics
    requests: RequestSummaryMetrics
    transfers: TransferSummaryMetrics
