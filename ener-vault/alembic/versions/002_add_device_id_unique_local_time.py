"""Add device_id and unique constraint on (device_id, local_time).

Revision ID: 002_device_id_unique
Revises: 001_initial
Create Date: 2026-04-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_device_id_unique"
down_revision: str | Sequence[str] | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "measurements",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="energy_meters",
    )
    op.execute(
        sa.text(
            "UPDATE energy_meters.measurements SET device_id = uuid_generate_v1() "
            "WHERE device_id IS NULL"
        )
    )
    op.alter_column(
        "measurements",
        "device_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        schema="energy_meters",
    )
    op.create_unique_constraint(
        "uq_measurements_device_id_local_time",
        "measurements",
        ["device_id", "local_time"],
        schema="energy_meters",
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN energy_meters.measurements.device_id IS "
            "'Logical identifier of the energy meter or device that produced this reading (UUID).'"
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_measurements_device_id_local_time",
        "measurements",
        schema="energy_meters",
        type_="unique",
    )
    op.drop_column("measurements", "device_id", schema="energy_meters")
