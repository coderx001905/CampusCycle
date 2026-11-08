"""Add request approval and cancellation metadata.

Revision ID: a73c5f91d2e4
Revises: c81f23a7d940
"""
from alembic import op
import sqlalchemy as sa

revision = "a73c5f91d2e4"
down_revision = "c81f23a7d940"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        foreign_keys_enabled = bind.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        if foreign_keys_enabled:
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            with op.batch_alter_table("requests", recreate="always") as batch:
                batch.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
                batch.add_column(sa.Column("approved_quantity", sa.Integer(), nullable=True))
                batch.add_column(sa.Column("cancellation_requested_by_user_id", sa.Integer(), nullable=True))
                batch.add_column(sa.Column("cancellation_requested_at", sa.DateTime(), nullable=True))
                batch.add_column(sa.Column("cancellation_reason", sa.Text(), nullable=True))
                batch.add_column(sa.Column("cancellation_reviewed_by_user_id", sa.Integer(), nullable=True))
                batch.add_column(sa.Column("cancellation_reviewed_at", sa.DateTime(), nullable=True))
                batch.add_column(sa.Column("cancellation_previous_status", sa.String(length=30), nullable=True))
                batch.add_column(sa.Column("cancellation_decision", sa.String(length=20), nullable=True))
                batch.create_foreign_key("fk_requests_cancellation_requested_by_user_id_users", "users", ["cancellation_requested_by_user_id"], ["id"], ondelete="RESTRICT")
                batch.create_foreign_key("fk_requests_cancellation_reviewed_by_user_id_users", "users", ["cancellation_reviewed_by_user_id"], ["id"], ondelete="RESTRICT")
                batch.create_check_constraint("ck_requests_approved_quantity", "approved_quantity IS NULL OR (approved_quantity > 0 AND approved_quantity <= requested_quantity)")
                batch.create_check_constraint("ck_requests_cancellation_decision", "cancellation_decision IS NULL OR cancellation_decision IN ('approved', 'rejected')")
                batch.create_check_constraint("ck_requests_cancellation_review_pair", "(cancellation_reviewed_at IS NULL AND cancellation_reviewed_by_user_id IS NULL AND cancellation_decision IS NULL) OR (cancellation_reviewed_at IS NOT NULL AND cancellation_reviewed_by_user_id IS NOT NULL AND cancellation_decision IS NOT NULL)")
                batch.create_check_constraint("ck_requests_cancellation_submission_fields", "(cancellation_requested_at IS NULL AND cancellation_requested_by_user_id IS NULL AND cancellation_reason IS NULL AND cancellation_previous_status IS NULL) OR (cancellation_requested_at IS NOT NULL AND cancellation_requested_by_user_id IS NOT NULL AND cancellation_reason IS NOT NULL AND cancellation_previous_status IS NOT NULL)")
                batch.create_check_constraint("ck_requests_rejection_reason_state", "rejection_reason IS NULL OR (status = 'rejected' AND reviewed_at IS NOT NULL AND reviewed_by_user_id IS NOT NULL)")
        finally:
            if foreign_keys_enabled:
                bind.exec_driver_sql("PRAGMA foreign_keys=ON")
        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").all()
        if violations:
            raise RuntimeError(f"Foreign-key violations after request workflow migration: {violations}")


def downgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        foreign_keys_enabled = bind.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        if foreign_keys_enabled:
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            with op.batch_alter_table("requests", recreate="always") as batch:
                batch.drop_constraint("ck_requests_cancellation_review_pair", type_="check")
                batch.drop_constraint("ck_requests_cancellation_submission_fields", type_="check")
                batch.drop_constraint("ck_requests_rejection_reason_state", type_="check")
                batch.drop_constraint("ck_requests_cancellation_decision", type_="check")
                batch.drop_constraint("ck_requests_approved_quantity", type_="check")
                batch.drop_constraint("fk_requests_cancellation_reviewed_by_user_id_users", type_="foreignkey")
                batch.drop_constraint("fk_requests_cancellation_requested_by_user_id_users", type_="foreignkey")
                for name in (
                    "cancellation_decision", "cancellation_previous_status", "cancellation_reviewed_at",
                    "cancellation_reviewed_by_user_id", "cancellation_reason", "cancellation_requested_at",
                    "cancellation_requested_by_user_id", "approved_quantity", "rejection_reason",
                ):
                    batch.drop_column(name)
        finally:
            if foreign_keys_enabled:
                bind.exec_driver_sql("PRAGMA foreign_keys=ON")
        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").all()
        if violations:
            raise RuntimeError(f"Foreign-key violations after request workflow downgrade: {violations}")
