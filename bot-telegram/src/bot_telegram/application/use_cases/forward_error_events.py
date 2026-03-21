from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bot_telegram.application.services.event_table_formatter import EventTableFormatter
from bot_telegram.domain.enums.alert_level import AlertLevel

if TYPE_CHECKING:
    from bot_telegram.domain.interfaces.ports import ErrorNotifier, EventPayloadParser

logger = logging.getLogger(__name__)


class ForwardErrorEventsUseCase:
    """Parse MQTT payloads and notify Telegram only for ERROR level."""

    def __init__(
        self,
        parser: "EventPayloadParser",
        notifier: "ErrorNotifier",
        formatter: EventTableFormatter | None = None,
    ) -> None:
        self._parser = parser
        self._notifier = notifier
        self._formatter = formatter or EventTableFormatter()

    def handle_payload(self, payload: bytes) -> None:
        event = self._parser.try_parse(payload)
        if event is None:
            return
        if event.level is not AlertLevel.ERROR:
            logger.info(
                "Event skipped (only ERROR is sent to Telegram): id=%s level=%s source=%s",
                event.id,
                event.level.value,
                event.source,
            )
            return
        html = self._formatter.format_error_table(event)
        logger.info(
            "Sending ERROR event id=%s source=%s to Telegram",
            event.id,
            event.source,
        )
        self._notifier.notify_error_event(event, html)
