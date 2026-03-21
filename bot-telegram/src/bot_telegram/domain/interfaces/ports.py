from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot_telegram.domain.entities.event import Event


class EventPayloadParser(ABC):
    """Parse external payload bytes into a domain Event or fail."""

    @abstractmethod
    def parse(self, payload: bytes) -> "Event":
        """Raise ValueError if payload is not a valid event."""

    @abstractmethod
    def try_parse(self, payload: bytes) -> "Event | None":
        """Return None if payload cannot be parsed (non-fatal)."""


class ErrorNotifier(ABC):
    """Send a formatted notification for a critical event."""

    @abstractmethod
    def notify_error_event(self, event: "Event", message_html: str) -> None:
        """Deliver notification; raise on transport failure."""
