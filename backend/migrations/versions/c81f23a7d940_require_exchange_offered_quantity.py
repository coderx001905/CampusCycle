"""Require a non-null offered quantity for exchange requests.

Revision ID: c81f23a7d940
Revises: f4a6d9c123ab
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c81f23a7d940"
down_revision: Union[str, None] = "f4a6d9c123ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_requests_exchange_offer_fields"
CORRECTED_CHECK = (
    "(request_type = 'exchange' AND offered_resource_id IS NOT NULL "
    "AND offered_quantity IS NOT NULL AND offered_quantity > 0) OR "
    "(request_type IN ('donation', 'purchase_enquiry') "
    "AND offered_resource_id IS NULL AND offered_quantity IS NULL)"
)


def upgrade() -> None:
    bind = op.get_bind()
    invalid_rows = bind.execute(
        sa.text(
            "SELECT id FROM requests WHERE "
            "CASE "
            "WHEN request_type = 'exchange' THEN "
            "offered_resource_id IS NOT NULL AND offered_quantity IS NOT NULL AND offered_quantity > 0 "
            "WHEN request_type IN ('donation', 'purchase_enquiry') THEN "
            "offered_resource_id IS NULL AND offered_quantity IS NULL "
            "ELSE 0 END = 0 ORDER BY id LIMIT 1"
        )
    ).first()
    if invalid_rows is not None:
        raise RuntimeError(
            "Cannot apply exchange-offer integrity correction: existing request "
            f"id={invalid_rows[0]} violates the approved offered-resource/quantity rules. "
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
    with op.get_context().autocommit_block():
        bind = op.get_bind()
        foreign_keys_enabled = bind.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        if foreign_keys_enabled:
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            with op.batch_alter_table("requests", recreate="always") as batch_op:
                batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
                batch_op.create_check_constraint(
                    CONSTRAINT_NAME,
                    "(request_type = 'exchange' AND offered_resource_id IS NOT NULL "
                    "AND offered_quantity > 0) OR "
                    "(request_type IN ('donation', 'purchase_enquiry') "
                    "AND offered_resource_id IS NULL AND offered_quantity IS NULL)",
                )
        finally:
            if foreign_keys_enabled:
                bind.exec_driver_sql("PRAGMA foreign_keys=ON")
        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").all()
        if violations:
            raise RuntimeError(
                f"Foreign-key violations after request constraint downgrade: {violations}"
            )
