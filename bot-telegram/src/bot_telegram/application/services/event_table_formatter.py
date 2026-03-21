from __future__ import annotations

import json
from typing import Any, Final

from bot_telegram.domain.entities.event import Event

_MAX_PRE_BODY: Final[int] = 3500


def _format_id(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _escape_telegram_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class EventTableFormatter:
    """Build monospace table text for Telegram HTML <pre> blocks."""

    def format_error_table(self, event: Event) -> str:
        metadata_str = json.dumps(event.metadata, ensure_ascii=False, indent=2, sort_keys=True)
        rows = [
            ("id", _format_id(event.id)),
            ("source", event.source),
            ("level", event.level.value),
            ("status", event.status.value),
            ("timestamp", event.timestamp),
            ("metadata", metadata_str),
        ]
        key_width = max(len(k) for k, _ in rows)
        lines = ["Ops Beacon — ERROR", "=" * 40]
        for key, value in rows:
            value_lines = value.splitlines() or [""]
            first = f"{key.ljust(key_width)} | {value_lines[0]}"
            lines.append(first)
            for extra in value_lines[1:]:
                lines.append(f"{' ' * key_width} | {extra}")
        body = "\n".join(lines)
        if len(body) > _MAX_PRE_BODY:
            body = body[: _MAX_PRE_BODY] + "\n…(truncated)"
        inner = _escape_telegram_html(body)
        return f"<pre>{inner}</pre>"
