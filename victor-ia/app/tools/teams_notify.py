"""Notify the operations team in Microsoft Teams via Power Automate (webhook URL from env).

TEAMS_WEBHOOK_URL must point to the flow that delivers messages to the **operaciones** channel
(or equivalent) so on-call / ops staff see alerts about the stack.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from langchain_core.tools import BaseTool, tool

from app.config.conf import CONFIG

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_BODY = 6000


def _message_card(*, title: str, body: str, subtitle: str | None) -> dict[str, Any]:
    """Office 365 Connector MessageCard — renders with title, facts, and markdown body in Teams."""

    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    safe_body = body.strip()[:_MAX_BODY]
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "6264A7",
        "summary": title[:200] if title else "Victor IA · operación",
        "sections": [
            {
                "activityTitle": title or "Victor IA",
                "activitySubtitle": subtitle or "Equipo de operación · ops-beacon",
                "facts": [
                    {"name": "Destino", "value": "Canal de operación (Teams)"},
                    {"name": "Hora (UTC)", "value": ts},
                ],
                "text": safe_body,
                "markdown": True,
            },
        ],
    }


@tool
def teams_send_notification(
    message: str,
    title: str | None = None,
) -> str:
    """Notify the **operations team** (equipo de operación) in Microsoft Teams.

    TEAMS_WEBHOOK_URL is the Power Automate HTTP trigger that posts into the ops team’s channel
    (alerts for on-call / operations, not a general-purpose chat). Use when the user wants to
    alert operations, escalate, or broadcast an operational summary. Sends a MessageCard (title,
    destino, hora UTC, cuerpo). Requires TEAMS_WEBHOOK_URL in the service environment.
    """
    url = CONFIG.TEAMS_WEBHOOK_URL
    if url is None or not str(url.get_secret_value()).strip():
        return json.dumps(
            {
                "ok": False,
                "error": "TEAMS_WEBHOOK_URL is not set; add the Power Automate URL for the operations team Teams channel to config/.env.",
            },
            ensure_ascii=False,
        )

    text = message.strip()
    if not text:
        return json.dumps({"ok": False, "error": "message must not be empty"}, ensure_ascii=False)

    card_title = (title.strip() if title and title.strip() else "Victor IA")
    payload = _message_card(title=card_title, body=text, subtitle=None)
    webhook = str(url.get_secret_value()).strip()

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                webhook,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
    except httpx.RequestError as e:
        logger.exception("Teams webhook POST failed")
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    out: dict[str, Any] = {"ok": r.is_success, "status_code": r.status_code}
    try:
        out["body"] = r.json()
    except Exception:
        out["body"] = (r.text or "")[:2048]
    return json.dumps(out, ensure_ascii=False)


TOOLS_TEAMS: list[BaseTool] = [teams_send_notification]
