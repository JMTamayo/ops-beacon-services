"""fred-ops PUB mode: simulate energy meter and publish JSON periodically."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from fred_ops import FredOps

logger = logging.getLogger(__name__)

app = FredOps()

_BOGOTA = ZoneInfo("America/Bogota")
_started = False

# Mutable simulation state (persists across execute calls)
_state = {
    "active_energy_kwh": 7.26,
}


def _format_local_timestamptz(dt: datetime) -> str:
    """Format like 2026-04-13T13:15:54.735-0500."""
    ms = dt.microsecond // 1000
    base = dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{ms:03d}"
    offset = dt.strftime("%z")
    return base + offset


@app.execute
async def execute(output, **kwargs) -> object:
    global _started
    interval = float(kwargs.get("interval_seconds", 60))

    if _started:
        await asyncio.sleep(interval)
    _started = True

    voltage = 120.0 + random.uniform(-2.0, 2.0)
    current = max(0.0, random.uniform(0.0, 8.0))
    power_factor = random.uniform(0.85, 1.0) if current > 0.01 else 0.0
    active_power = round(voltage * current * power_factor, 3)
    increment_kwh = active_power / 1000.0 * (interval / 3600.0)
    _state["active_energy_kwh"] = round(_state["active_energy_kwh"] + increment_kwh, 4)

    now = datetime.now(_BOGOTA)
    local_ts = _format_local_timestamptz(now)

    payload = output(
        local_timestamptz=local_ts,
        data={
            "voltage": round(voltage, 2),
            "current": round(current, 3),
            "active_power": active_power,
            "active_energy": _state["active_energy_kwh"],
            "frequency": 60,
            "power_factor": round(power_factor, 3),
        },
    )
    logger.info(
        "Publishing simulator reading ts=%s active_energy=%s",
        local_ts,
        _state["active_energy_kwh"],
    )
    return payload
