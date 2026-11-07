from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("quantity_total >= 0 AND quantity_available >= 0 AND quantity_reserved >= 0", name="ck_resources_quantities_nonnegative"),
        CheckConstraint("quantity_available + quantity_reserved = quantity_total", name="ck_resources_quantity_balance"),
        CheckConstraint("quantity_reserved <= quantity_total", name="ck_resources_reserved_lte_total"),
        CheckConstraint("transfer_type IN ('donation', 'exchange', 'sale')", name="ck_resources_transfer_type"),
        CheckConstraint("status IN ('active', 'inactive', 'depleted')", name="ck_resources_status"),
        Index("ix_resources_college_id_status", "college_id", "status"),
        Index("ix_resources_category_status", "category", "status"),
        Index("ix_resources_transfer_type_status", "transfer_type", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="RESTRICT"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity_total: Mapped[int] = mapped_column(nullable=False)
    quantity_available: Mapped[int] = mapped_column(nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    transfer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    indicative_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    image_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now, server_default=func.current_timestamp())

    college: Mapped["College"] = relationship(back_populates="resources")
    created_by: Mapped["User"] = relationship(back_populates="created_resources")
    requested_in: Mapped[list["Request"]] = relationship(back_populates="resource", foreign_keys="Request.resource_id")
    offered_in: Mapped[list["Request"]] = relationship(back_populates="offered_resource", foreign_keys="Request.offered_resource_id")
    transfers: Mapped[list["Transfer"]] = relationship(back_populates="resource")
