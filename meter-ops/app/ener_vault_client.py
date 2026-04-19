"""HTTP client for ener-vault API: base URL, measurement payload, and POST."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx

from app.models import MeterReading

logger = logging.getLogger(__name__)

# Same host/port as ener-vault in docker-compose (service `ener-vault`, port 8080).
ENER_VAULT_BASE_URL = "http://ener-vault:8080"

_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_BODY_LOG = 2048

# Offsets like -0500 or +0530 (no colon) at end of string — Python's fromisoformat wants -05:00.
_OFFSET_NO_COLON = re.compile(r"([+-])(\d{2})(\d{2})$")


def _parse_local_timestamptz(value: str) -> datetime:
    """Parse meter `local_timestamptz` into a timezone-aware datetime."""
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    m = _OFFSET_NO_COLON.search(s)
    if m:
        s = s[: m.start()] + f"{m.group(1)}{m.group(2)}:{m.group(3)}"
    return datetime.fromisoformat(s)


def _measurement_create_body(device_id: UUID, reading: MeterReading) -> dict[str, Any]:
    """JSON body for `POST /v1/measurements` (MeasurementCreate)."""
    local_time = _parse_local_timestamptz(reading.local_timestamptz)
    d = reading.data
    return {
        "device_id": str(device_id),
        "local_time": local_time.isoformat(),
        "voltage": d.voltage,
        "current": d.current,
        "active_power": d.active_power,
        "active_energy": d.active_energy,
        "frequency": d.frequency,
        "power_factor": d.power_factor,
    }


async def post_meter_reading(device_id: UUID, reading: MeterReading) -> bool:
    """Build measurement JSON and POST to ener-vault. Returns True on 2xx; logs and returns False on failure."""
    try:
        body = _measurement_create_body(device_id, reading)
    except ValueError as e:
        logger.error("ener-vault: invalid local_timestamptz: %s", e)
        return False

    url = f"{ENER_VAULT_BASE_URL.rstrip('/')}/v1/measurements"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            response = await client.post(url, json=body)
    except httpx.RequestError as e:
        logger.error(
            "ener-vault request failed (url=%s): %s",
            url,
            e,
        )
        return False

    if response.is_success:
        return True

    text = response.text
    if len(text) > _MAX_BODY_LOG:
        text = text[:_MAX_BODY_LOG] + "…"
    logger.error(
        "ener-vault measurement create failed (url=%s status=%s): %s",
        url,
        response.status_code,
        text,
    )
    return False
