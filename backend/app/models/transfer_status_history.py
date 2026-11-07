from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class TransferStatusHistory(Base):
    __tablename__ = "transfer_status_history"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'system')", name="ck_transfer_status_history_actor_type"),
        Index("ix_transfer_status_history_transfer_id_changed_at", "transfer_id", "changed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id", ondelete="RESTRICT"), nullable=False)
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())

    transfer: Mapped["Transfer"] = relationship(back_populates="status_history")
    changed_by: Mapped["User | None"] = relationship(back_populates="transfer_history_entries")
