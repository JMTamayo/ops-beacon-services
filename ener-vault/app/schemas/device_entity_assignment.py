import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class DeviceEntityAssignmentCreate(BaseModel):
    device_id: uuid.UUID
    entity_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _ended_after_started(self) -> Self:
        if self.ended_at is not None and self.ended_at <= self.started_at:
            raise ValueError("ended_at must be after started_at when provided.")
        return self


class DeviceEntityAssignmentUpdate(BaseModel):
    device_id: uuid.UUID | None = None
    entity_id: uuid.UUID | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _ended_after_started(self) -> Self:
        # If both ends provided, validate; if only one, domain layer merges with existing row.
        if self.started_at is not None and self.ended_at is not None and self.ended_at <= self.started_at:
            raise ValueError("ended_at must be after started_at when both are provided.")
        return self


class DeviceEntityAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    entity_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    description: str | None
    created_at: datetime
    updated_at: datetime | None
