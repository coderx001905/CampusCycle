"""Remove status defaults not specified by the approved schema.

Revision ID: f4a6d9c123ab
Revises: 889848499f56
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a6d9c123ab"
down_revision: Union[str, None] = "889848499f56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    defaults_to_remove = {
        (table, column)
        for table, column in (
            ("resources", "status"),
            ("requests", "status"),
            ("transfers", "status"),
            ("transfers", "dispute_status"),
        )
        if next(
            item["default"]
            for item in sa.inspect(bind).get_columns(table)
            if item["name"] == column
        ) is not None
    }
    if not defaults_to_remove:
        return

    with op.get_context().autocommit_block():
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            for table, column in sorted(defaults_to_remove):
                with op.batch_alter_table(table) as batch:
                    batch.alter_column(
                        column,
                        existing_type=sa.String(),
                        existing_nullable=False,
                        server_default=None,
                    )
        finally:
            bind.exec_driver_sql("PRAGMA foreign_keys=ON")
        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").all()
        if violations:
            raise RuntimeError(f"Foreign-key violations after default cleanup: {violations}")


def downgrade() -> None:
    # The checked-in initial revision has no such defaults, so this revision is
    # a no-op on clean installs and a corrective cleanup on legacy dev installs.
    pass
