"""Add nullable updated_at and BEFORE UPDATE triggers on devices and measurements.

Revision ID: 005_updated_at
Revises: 004_devices_catalog
Create Date: 2026-04-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_updated_at"
down_revision: str | Sequence[str] | None = "004_devices_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="energy_meters",
    )
    op.add_column(
        "measurements",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="energy_meters",
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION energy_meters.touch_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at := now();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_devices_updated_at ON energy_meters.devices;
        CREATE TRIGGER trg_devices_updated_at
        BEFORE UPDATE ON energy_meters.devices
        FOR EACH ROW
        EXECUTE FUNCTION energy_meters.touch_updated_at();
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_measurements_updated_at ON energy_meters.measurements;
        CREATE TRIGGER trg_measurements_updated_at
        BEFORE UPDATE ON energy_meters.measurements
        FOR EACH ROW
        EXECUTE FUNCTION energy_meters.touch_updated_at();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_measurements_updated_at ON energy_meters.measurements;"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_devices_updated_at ON energy_meters.devices;")
    op.execute("DROP FUNCTION IF EXISTS energy_meters.touch_updated_at();")

    op.drop_column("measurements", "updated_at", schema="energy_meters")
    op.drop_column("devices", "updated_at", schema="energy_meters")
