"""B-tree index on local_time for date-range listing.

The existing unique constraint on (device_id, local_time) already provides a
composite index suited to filter by device_id and local_time; this index
optimizes queries that filter only by local_time (or by upper bound on time).

Revision ID: 003_index_local_time
Revises: 002_device_id_unique
Create Date: 2026-04-18

"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_index_local_time"
down_revision: str | Sequence[str] | None = "002_device_id_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_measurements_local_time",
        "measurements",
        ["local_time"],
        schema="energy_meters",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_measurements_local_time",
        table_name="measurements",
        schema="energy_meters",
    )
