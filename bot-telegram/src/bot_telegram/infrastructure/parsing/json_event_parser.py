from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from bot_telegram.domain.entities.event import Event
from bot_telegram.domain.enums.alert_level import AlertLevel
from bot_telegram.domain.enums.event_status import EventStatus
from bot_telegram.domain.interfaces.ports import EventPayloadParser

logger = logging.getLogger(__name__)

_MAX_LOG_PAYLOAD = 400


class _EventJsonModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Any
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    level: str
    timestamp: str
    status: str

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_as_string(cls, value: object) -> str:
        text = str(value).strip()
        if not text:
            msg = "timestamp must be a non-empty string"
            raise ValueError(msg)
        return text

    def to_domain(self) -> Event:
        return Event(
            id=self.id,
            source=self.source.strip(),
            metadata=dict(self.metadata),
            level=AlertLevel.from_string(self.level),
            timestamp=self.timestamp,
            status=EventStatus.from_string(self.status),
        )


class JsonEventParser(EventPayloadParser):
    """Parse MQTT JSON payloads into domain events."""

    def parse(self, payload: bytes) -> Event:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        try:
            model = _EventJsonModel.model_validate(data)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        return model.to_domain()

    def try_parse(self, payload: bytes) -> Event | None:
        try:
            return self.parse(payload)
        except ValueError as exc:
            preview = payload[:_MAX_LOG_PAYLOAD]
            try:
                text = preview.decode("utf-8", errors="replace")
            except Exception:
                text = repr(preview)
            logger.warning(
                "MQTT payload is not a valid ops-beacon event: %s | preview=%r",
                exc,
                text,
            )
            return None
