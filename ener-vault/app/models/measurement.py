from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Double, ForeignKey, Index, Uuid, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device import Device


class Measurement(Base):
    """ORM model for `energy_meters.measurements`."""

    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "local_time",
            name="uq_measurements_device_id_local_time",
        ),
        Index("ix_measurements_local_time", "local_time"),
    )

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
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("energy_meters.devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    local_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    voltage: Mapped[float] = mapped_column(Double, nullable=False)
    current: Mapped[float] = mapped_column(Double, nullable=False)
    active_power: Mapped[float] = mapped_column(Double, nullable=False)
    active_energy: Mapped[float] = mapped_column(Double, nullable=False)
    frequency: Mapped[float] = mapped_column(Double, nullable=False)
    power_factor: Mapped[float] = mapped_column(Double, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="measurements")
