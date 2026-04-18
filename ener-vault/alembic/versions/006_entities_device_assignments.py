"""Entities catalog, device_entity_assignments, exclusion constraint, seed data.

Revision ID: 006_entities_assignments
Revises: 005_updated_at
Create Date: 2026-04-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "006_entities_assignments"
down_revision: str | Sequence[str] | None = "005_updated_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED_NAMES = (
    "TV",
    "Refrigerator",
    "Lamp",
    "Washing machine",
    "Dryer",
    "Microwave",
    "Oven",
    "Air conditioner",
    "Fan",
    "Computer",
    "Coffee maker",
    "Blender",
    "Iron",
    "Water heater",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    op.create_table(
        "entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v1()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_entities_name"),
        schema="energy_meters",
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_entities_updated_at ON energy_meters.entities;
        CREATE TRIGGER trg_entities_updated_at
        BEFORE UPDATE ON energy_meters.entities
        FOR EACH ROW
        EXECUTE FUNCTION energy_meters.touch_updated_at();
        """
    )

    bind = op.get_bind()
    for label in _SEED_NAMES:
        bind.execute(
            text(
                "INSERT INTO energy_meters.entities (id, created_at, name) "
                "VALUES (uuid_generate_v1(), now(), :name)"
            ),
            {"name": label},
        )

    op.create_table(
        "device_entity_assignments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v1()"),
            nullable=False,
        ),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["energy_meters.devices.id"],
            name="fk_dea_device_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["energy_meters.entities.id"],
            name="fk_dea_entity_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ck_dea_ended_after_started",
        ),
        schema="energy_meters",
    )

    op.execute(
        """
        ALTER TABLE energy_meters.device_entity_assignments
        ADD CONSTRAINT ex_dea_no_overlap_per_device
        EXCLUDE USING gist (
          device_id WITH =,
          tstzrange(
            started_at,
            COALESCE(ended_at, 'infinity'::timestamptz),
            '[)'
          ) WITH &&
        );
        """
    )

    op.create_index(
        "ix_dea_device_started",
        "device_entity_assignments",
        ["device_id", "started_at"],
        schema="energy_meters",
        postgresql_ops={"started_at": "DESC"},
    )
    op.create_index(
        "ix_dea_entity_started",
        "device_entity_assignments",
        ["entity_id", "started_at"],
        schema="energy_meters",
        postgresql_ops={"started_at": "DESC"},
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_device_entity_assignments_updated_at
          ON energy_meters.device_entity_assignments;
        CREATE TRIGGER trg_device_entity_assignments_updated_at
        BEFORE UPDATE ON energy_meters.device_entity_assignments
        FOR EACH ROW
        EXECUTE FUNCTION energy_meters.touch_updated_at();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_device_entity_assignments_updated_at "
        "ON energy_meters.device_entity_assignments;"
    )
    op.drop_index("ix_dea_entity_started", table_name="device_entity_assignments", schema="energy_meters")
    op.drop_index("ix_dea_device_started", table_name="device_entity_assignments", schema="energy_meters")
    op.drop_table("device_entity_assignments", schema="energy_meters")

    op.execute("DROP TRIGGER IF EXISTS trg_entities_updated_at ON energy_meters.entities;")
    op.drop_table("entities", schema="energy_meters")
