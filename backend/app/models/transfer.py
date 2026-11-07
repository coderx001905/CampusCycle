from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("transfer_leg IN ('requested_resource', 'offered_resource')", name="ck_transfers_leg"),
        CheckConstraint("status IN ('preparing', 'dispatched', 'partially_received', 'disputed', 'received', 'completed', 'cancellation_pending', 'cancelled')", name="ck_transfers_status"),
        CheckConstraint("dispute_status IN ('none', 'open', 'resolved')", name="ck_transfers_dispute_status"),
        CheckConstraint("dispute_outcome IS NULL OR dispute_outcome IN ('accept_report', 'replacement_approved', 'claim_rejected')", name="ck_transfers_dispute_outcome"),
        CheckConstraint("cancellation_decision IS NULL OR cancellation_decision IN ('approved', 'rejected')", name="ck_transfers_cancellation_decision"),
        CheckConstraint("quantity > 0", name="ck_transfers_quantity_positive"),
        CheckConstraint("(quantity_received_good IS NULL OR quantity_received_good >= 0) AND (quantity_damaged IS NULL OR quantity_damaged >= 0) AND (quantity_missing IS NULL OR quantity_missing >= 0)", name="ck_transfers_received_quantities_nonnegative"),
        CheckConstraint("COALESCE(quantity_received_good, 0) + COALESCE(quantity_damaged, 0) + COALESCE(quantity_missing, 0) <= quantity", name="ck_transfers_received_quantities_lte_batch"),
        Index("ix_transfers_request_id_transfer_leg_status", "request_id", "transfer_leg", "status"),
        Index("ix_transfers_source_college_id_status", "source_college_id", "status"),
        Index("ix_transfers_destination_college_id_status", "destination_college_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="RESTRICT"), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False)
    transfer_leg: Mapped[str] = mapped_column(String(30), nullable=False)
    source_college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False)
    destination_college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    quantity_received_good: Mapped[int | None] = mapped_column()
    quantity_damaged: Mapped[int | None] = mapped_column()
    quantity_missing: Mapped[int | None] = mapped_column()
    dispute_status: Mapped[str] = mapped_column(String(30), nullable=False)
    dispute_resolution: Mapped[str | None] = mapped_column(Text)
    dispute_outcome: Mapped[str | None] = mapped_column(String(30))
    replacement_for_transfer_id: Mapped[int | None] = mapped_column(ForeignKey("transfers.id", ondelete="RESTRICT"))
    dispute_resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    dispute_resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    dispatched_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    received_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    pickup_or_delivery_date: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    dispatch_notes: Mapped[str | None] = mapped_column(Text)
    receipt_confirmation: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancellation_requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    cancellation_reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancellation_decision: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    request: Mapped["Request"] = relationship(back_populates="transfers")
    resource: Mapped["Resource"] = relationship(back_populates="transfers")
    source_college: Mapped["College"] = relationship(back_populates="source_transfers", foreign_keys=[source_college_id])
    destination_college: Mapped["College"] = relationship(back_populates="destination_transfers", foreign_keys=[destination_college_id])
    replacement_for: Mapped["Transfer | None"] = relationship(remote_side="Transfer.id", back_populates="replacement_transfers", foreign_keys=[replacement_for_transfer_id])
    replacement_transfers: Mapped[list["Transfer"]] = relationship(back_populates="replacement_for", foreign_keys=[replacement_for_transfer_id])
    dispute_resolved_by: Mapped["User | None"] = relationship(back_populates="dispute_reviews", foreign_keys=[dispute_resolved_by_user_id])
    created_by: Mapped["User"] = relationship(back_populates="created_transfers", foreign_keys=[created_by_user_id])
    dispatched_by: Mapped["User | None"] = relationship(back_populates="dispatched_transfers", foreign_keys=[dispatched_by_user_id])
    received_by: Mapped["User | None"] = relationship(back_populates="received_transfers", foreign_keys=[received_by_user_id])
    cancellation_requested_by: Mapped["User | None"] = relationship(back_populates="cancellation_requests", foreign_keys=[cancellation_requested_by_user_id])
    cancellation_reviewed_by: Mapped["User | None"] = relationship(back_populates="cancellation_reviews", foreign_keys=[cancellation_reviewed_by_user_id])
    status_history: Mapped[list["TransferStatusHistory"]] = relationship(back_populates="transfer")
