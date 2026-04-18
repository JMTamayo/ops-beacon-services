import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    serial_number: str | None = Field(default=None, max_length=128)
    is_active: bool = True


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    name: str | None
    serial_number: str | None
    is_active: bool
