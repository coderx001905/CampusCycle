from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint("requested_quantity > 0", name="ck_requests_requested_quantity_positive"),
        CheckConstraint(
            "(request_type = 'exchange' AND offered_resource_id IS NOT NULL "
            "AND offered_quantity IS NOT NULL AND offered_quantity > 0) OR "
            "(request_type IN ('donation', 'purchase_enquiry') AND offered_resource_id IS NULL AND offered_quantity IS NULL)",
            name="ck_requests_exchange_offer_fields",
        ),
        CheckConstraint("request_type IN ('donation', 'exchange', 'purchase_enquiry')", name="ck_requests_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected', 'in_progress', 'awaiting_resolution', 'completed', 'cancelled')", name="ck_requests_status"),
        CheckConstraint("approved_quantity IS NULL OR (approved_quantity > 0 AND approved_quantity <= requested_quantity)", name="ck_requests_approved_quantity"),
        CheckConstraint("cancellation_decision IS NULL OR cancellation_decision IN ('approved', 'rejected')", name="ck_requests_cancellation_decision"),
        CheckConstraint("(cancellation_reviewed_at IS NULL AND cancellation_reviewed_by_user_id IS NULL AND cancellation_decision IS NULL) OR (cancellation_reviewed_at IS NOT NULL AND cancellation_reviewed_by_user_id IS NOT NULL AND cancellation_decision IS NOT NULL)", name="ck_requests_cancellation_review_pair"),
        CheckConstraint("(cancellation_requested_at IS NULL AND cancellation_requested_by_user_id IS NULL AND cancellation_reason IS NULL AND cancellation_previous_status IS NULL) OR (cancellation_requested_at IS NOT NULL AND cancellation_requested_by_user_id IS NOT NULL AND cancellation_reason IS NOT NULL AND cancellation_previous_status IS NOT NULL)", name="ck_requests_cancellation_submission_fields"),
        CheckConstraint("rejection_reason IS NULL OR (status = 'rejected' AND reviewed_at IS NOT NULL AND reviewed_by_user_id IS NOT NULL)", name="ck_requests_rejection_reason_state"),
        Index("ix_requests_resource_id_status", "resource_id", "status"),
        Index("ix_requests_requesting_college_id_status", "requesting_college_id", "status"),
        Index("ix_requests_request_type_status", "request_type", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False)
    requesting_college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    offered_resource_id: Mapped[int | None] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"))
    requested_quantity: Mapped[int] = mapped_column(nullable=False)
    offered_quantity: Mapped[int | None] = mapped_column()
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    approved_quantity: Mapped[int | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    purchase_intent_confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    purchase_confirmed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    cancellation_reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancellation_previous_status: Mapped[str | None] = mapped_column(String(30))
    cancellation_decision: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.current_timestamp())

    resource: Mapped["Resource"] = relationship(back_populates="requested_in", foreign_keys=[resource_id])
    offered_resource: Mapped["Resource | None"] = relationship(back_populates="offered_in", foreign_keys=[offered_resource_id])
    requesting_college: Mapped["College"] = relationship(back_populates="requests")
    requested_by: Mapped["User"] = relationship(back_populates="submitted_requests", foreign_keys=[requested_by_user_id])
    reviewed_by: Mapped["User | None"] = relationship(back_populates="reviewed_requests", foreign_keys=[reviewed_by_user_id])
    purchase_confirmed_by: Mapped["User | None"] = relationship(back_populates="purchase_confirmed_requests", foreign_keys=[purchase_confirmed_by_user_id])
    cancellation_requested_by: Mapped["User | None"] = relationship(foreign_keys=[cancellation_requested_by_user_id])
    cancellation_reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[cancellation_reviewed_by_user_id])
    transfers: Mapped[list["Transfer"]] = relationship(back_populates="request")
