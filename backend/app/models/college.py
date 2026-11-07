from datetime import datetime

from sqlalchemy import CheckConstraint, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class College(Base):
    __tablename__ = "colleges"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected')",
            name="ck_colleges_verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default=text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now,
        server_default=func.current_timestamp()
    )

    users: Mapped[list["User"]] = relationship(back_populates="college", foreign_keys="User.college_id")
    resources: Mapped[list["Resource"]] = relationship(back_populates="college")
    requests: Mapped[list["Request"]] = relationship(back_populates="requesting_college")
    source_transfers: Mapped[list["Transfer"]] = relationship(
        back_populates="source_college", foreign_keys="Transfer.source_college_id"
    )
    destination_transfers: Mapped[list["Transfer"]] = relationship(
        back_populates="destination_college", foreign_keys="Transfer.destination_college_id"
    )
