from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.sql import column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('platform_admin', 'college_representative')", name="ck_users_role"),
        CheckConstraint(
            "(role = 'platform_admin' AND college_id IS NULL) OR "
            "(role = 'college_representative' AND college_id IS NOT NULL)",
            name="ck_users_role_college",
        ),
        Index("uq_users_email_lower", func.lower(column("email")), unique=True),
        Index("ix_users_college_id_is_active", "college_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int | None] = mapped_column(ForeignKey("colleges.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now,
        server_default=func.current_timestamp()
    )

    college: Mapped["College | None"] = relationship(back_populates="users", foreign_keys=[college_id])
    created_resources: Mapped[list["Resource"]] = relationship(back_populates="created_by")
    submitted_requests: Mapped[list["Request"]] = relationship(
        back_populates="requested_by", foreign_keys="Request.requested_by_user_id"
    )
    reviewed_requests: Mapped[list["Request"]] = relationship(
        back_populates="reviewed_by", foreign_keys="Request.reviewed_by_user_id"
    )
    purchase_confirmed_requests: Mapped[list["Request"]] = relationship(
        back_populates="purchase_confirmed_by", foreign_keys="Request.purchase_confirmed_by_user_id"
    )
    created_transfers: Mapped[list["Transfer"]] = relationship(
        back_populates="created_by", foreign_keys="Transfer.created_by_user_id"
    )
    dispatched_transfers: Mapped[list["Transfer"]] = relationship(
        back_populates="dispatched_by", foreign_keys="Transfer.dispatched_by_user_id"
    )
    received_transfers: Mapped[list["Transfer"]] = relationship(
        back_populates="received_by", foreign_keys="Transfer.received_by_user_id"
    )
    dispute_reviews: Mapped[list["Transfer"]] = relationship(
        back_populates="dispute_resolved_by", foreign_keys="Transfer.dispute_resolved_by_user_id"
    )
    cancellation_reviews: Mapped[list["Transfer"]] = relationship(
        back_populates="cancellation_reviewed_by", foreign_keys="Transfer.cancellation_reviewed_by_user_id"
    )
    cancellation_requests: Mapped[list["Transfer"]] = relationship(
        back_populates="cancellation_requested_by", foreign_keys="Transfer.cancellation_requested_by_user_id"
    )
    transfer_history_entries: Mapped[list["TransferStatusHistory"]] = relationship(
        back_populates="changed_by"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
