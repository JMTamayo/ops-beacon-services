from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device_entity_assignment import DeviceEntityAssignment


class Entity(Base):
    """Catalog row for a generic load type (e.g. TV, Refrigerator)."""

    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v1()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)

    device_assignments: Mapped[list["DeviceEntityAssignment"]] = relationship(
        "DeviceEntityAssignment",
        back_populates="entity",
        foreign_keys="DeviceEntityAssignment.entity_id",
    )
