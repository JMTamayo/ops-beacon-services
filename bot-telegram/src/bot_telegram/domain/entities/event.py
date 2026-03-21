from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bot_telegram.domain.enums.alert_level import AlertLevel
from bot_telegram.domain.enums.event_status import EventStatus


@dataclass(frozen=True, slots=True)
class Event:
    """Domain event aligned with ops-beacon."""

    id: Any
    source: str
    metadata: dict[str, Any]
    level: AlertLevel
    timestamp: str
    status: EventStatus

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must be non-empty")
        if not self.timestamp.strip():
            raise ValueError("timestamp must be non-empty")

    def is_error(self) -> bool:
        return self.level is AlertLevel.ERROR
