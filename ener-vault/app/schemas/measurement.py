import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MeasurementCreate(BaseModel):
    device_id: uuid.UUID = Field(description="Identifier of the energy meter or device (UUID).")
    local_time: datetime = Field(description="Instant the reading was taken on the meter/device clock.")
    voltage: float = Field(description="RMS or line voltage in volts (V).")
    current: float = Field(description="Current in amperes (A).")
    active_power: float = Field(description="Active (real) power in watts (W).")
    active_energy: float = Field(
        description="Active energy register reading; cumulative energy in watt-hours (Wh)."
    )
    frequency: float = Field(description="AC frequency in hertz (Hz).")
    power_factor: float = Field(description="Power factor (dimensionless, typically -1..1 or 0..1).")


class MeasurementUpdate(BaseModel):
    device_id: uuid.UUID | None = None
    local_time: datetime | None = None
    voltage: float | None = None
    current: float | None = None
    active_power: float | None = None
    active_energy: float | None = None
    frequency: float | None = None
    power_factor: float | None = None


class MeasurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    device_id: uuid.UUID
    local_time: datetime
    voltage: float
    current: float
    active_power: float
    active_energy: float
    frequency: float
    power_factor: float
