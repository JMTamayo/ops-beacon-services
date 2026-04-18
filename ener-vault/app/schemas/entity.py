import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EntityCreate(BaseModel):
    name: str = Field(min_length=1, description="Unique catalog label (e.g. Refrigerator).")


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    name: str
