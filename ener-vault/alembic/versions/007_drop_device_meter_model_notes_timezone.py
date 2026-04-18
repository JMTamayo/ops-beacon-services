"""Remove meter_model, notes, timezone from devices.

Revision ID: 007_drop_device_extra_cols
Revises: 006_entities_assignments
Create Date: 2026-04-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_drop_device_extra_cols"
down_revision: str | Sequence[str] | None = "006_entities_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("devices", "meter_model", schema="energy_meters")
    op.drop_column("devices", "notes", schema="energy_meters")
    op.drop_column("devices", "timezone", schema="energy_meters")


def downgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("meter_model", sa.String(length=128), nullable=True),
        schema="energy_meters",
    )
    op.add_column(
        "devices",
        sa.Column("notes", sa.Text(), nullable=True),
        schema="energy_meters",
    )
    op.add_column(
        "devices",
        sa.Column("timezone", sa.String(length=64), nullable=True),
        schema="energy_meters",
    )
