from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import UTCDateTime, utc_now
from app.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("uq_refresh_tokens_jti", "jti", unique=True),
        Index("uq_refresh_tokens_token_hash", "token_hash", unique=True),
        Index("ix_refresh_tokens_user_id_expires_at", "user_id", "expires_at"),
        Index("ix_refresh_tokens_token_family_id_revoked_at", "token_family_id", "revoked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    jti: Mapped[str] = mapped_column(String(100), nullable=False)
    token_family_id: Mapped[str] = mapped_column(String(100), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now, server_default=func.current_timestamp())
    replaced_by_token_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_tokens.id", ondelete="RESTRICT"))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(64))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    replaced_by: Mapped["RefreshToken | None"] = relationship(remote_side="RefreshToken.id", back_populates="replaces", foreign_keys=[replaced_by_token_id])
    replaces: Mapped[list["RefreshToken"]] = relationship(back_populates="replaced_by", foreign_keys=[replaced_by_token_id])
