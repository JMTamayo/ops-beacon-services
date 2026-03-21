from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from bot_telegram.domain.interfaces.ports import ErrorNotifier

if TYPE_CHECKING:
    from bot_telegram.domain.entities.event import Event

logger = logging.getLogger(__name__)

EXAMPLE_MESSAGE_HTML = (
    "<b>Ops Beacon — mensaje de prueba</b>\n"
    "<pre>Este mensaje lo envía el endpoint POST /telegram/example\n"
    "para verificar bot_token y chat_id sin pasar por MQTT.</pre>"
)


class TelegramNotifier(ErrorNotifier):
    """Send HTML messages via Telegram Bot API."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        *,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def _send_message_html(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        response = self._client.post(
            url,
            json={
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            logger.exception("Telegram API error: %s", response.text)
            raise
        logger.info("Telegram sendMessage OK (chat_id=%s)", self._chat_id)

    def notify_error_event(self, event: "Event", message_html: str) -> None:
        _ = event
        self._send_message_html(message_html)

    def send_example_message(self) -> None:
        """Send a fixed HTML message (for manual / HTTP checks)."""
        self._send_message_html(EXAMPLE_MESSAGE_HTML)

    def close(self) -> None:
        self._client.close()
