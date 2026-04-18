from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device_entity_assignment import DeviceEntityAssignment
    from app.models.measurement import Measurement


class Device(Base):
    """Catalog row for an energy meter / device that owns measurements."""

    __tablename__ = "devices"

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
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), server_default=text("true"), nullable=False)

    measurements: Mapped[list["Measurement"]] = relationship(
        "Measurement",
        back_populates="device",
        foreign_keys="Measurement.device_id",
    )
    entity_assignments: Mapped[list["DeviceEntityAssignment"]] = relationship(
        "DeviceEntityAssignment",
        back_populates="device",
        foreign_keys="DeviceEntityAssignment.device_id",
    )
