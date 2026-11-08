"""Enforce approved quantity integrity by request type.

Revision ID: 2d1946b08dd1
Revises: a73c5f91d2e4
Create Date: 2026-11-08 12:31:43.441510
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2d1946b08dd1"
down_revision: Union[str, None] = "a73c5f91d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_requests_approved_quantity"
CORRECTED_CHECK = (
    "approved_quantity IS NULL OR ("
    "approved_quantity > 0 AND ("
    "(request_type = 'donation' AND approved_quantity <= requested_quantity) OR "
    "(request_type IN ('exchange', 'purchase_enquiry') AND approved_quantity = requested_quantity)"
    "))"
)
PREVIOUS_CHECK = (
    "approved_quantity IS NULL OR (approved_quantity > 0 AND approved_quantity <= requested_quantity)"
)


def upgrade() -> None:
    bind = op.get_bind()
    invalid_rows = bind.execute(
        sa.text(
            "SELECT id FROM requests WHERE "
            "approved_quantity IS NOT NULL AND NOT ("
            "approved_quantity > 0 AND ("
            "(request_type = 'donation' AND approved_quantity <= requested_quantity) OR "
            "(request_type IN ('exchange', 'purchase_enquiry') AND approved_quantity = requested_quantity)"
            ")) ORDER BY id LIMIT 1"
        )
    ).first()
    if invalid_rows is not None:
        raise RuntimeError(
            "Cannot apply approved-quantity integrity correction: existing request "
            f"id={invalid_rows[0]} violates the approved-quantity rules. "
            "No request rows were changed."
        )

    foreign_keys_enabled = bind.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    with op.get_context().autocommit_block():
        if foreign_keys_enabled:
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            with op.batch_alter_table("requests", recreate="always") as batch_op:
                batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
                batch_op.create_check_constraint(CONSTRAINT_NAME, CORRECTED_CHECK)
        finally:
            if foreign_keys_enabled:
                bind.exec_driver_sql("PRAGMA foreign_keys=ON")

        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").all()
        if violations:
            raise RuntimeError(
                f"Foreign-key violations after request constraint migration: {violations}"
            )


def downgrade() -> None:
    bind = op.get_bind()
    invalid_rows = bind.execute(
        sa.text(
            "SELECT id FROM requests WHERE "
            "approved_quantity IS NOT NULL AND NOT ("
            "approved_quantity > 0 AND approved_quantity <= requested_quantity"
            ") ORDER BY id LIMIT 1"
        )
    ).first()
    if invalid_rows is not None:
        raise RuntimeError(
            "Cannot downgrade approved-quantity constraint: existing request "
            f"id={invalid_rows[0]} violates the previous approved-quantity rules. "
            "No request rows were changed."
        )

    foreign_keys_enabled = bind.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    with op.get_context().autocommit_block():
        if foreign_keys_enabled:
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            with op.batch_alter_table("requests", recreate="always") as batch_op:
                batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
                batch_op.create_check_constraint(CONSTRAINT_NAME, PREVIOUS_CHECK)
        finally:
            if foreign_keys_enabled:
                bind.exec_driver_sql("PRAGMA foreign_keys=ON")

        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").all()
        if violations:
            raise RuntimeError(
                f"Foreign-key violations after request constraint downgrade: {violations}"
            )
