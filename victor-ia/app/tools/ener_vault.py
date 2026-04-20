"""Tools that call the ener-vault HTTP API."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain_core.tools import BaseTool, tool

from app.config.conf import CONFIG

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _base_url() -> str:
    return CONFIG.ENER_VAULT_BASE_URL.rstrip("/")


def _get(path: str, params: dict[str, Any] | None = None) -> str:
    url = f"{_base_url()}{path}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(url, params=params)
    except httpx.RequestError as e:
        logger.exception("ener-vault GET failed: %s", url)
        return json.dumps({"ok": False, "error": str(e), "url": url})
    payload: dict[str, Any] = {"ok": r.is_success, "status_code": r.status_code, "url": url}
    try:
        payload["body"] = r.json()
    except Exception:
        payload["body"] = r.text[:4096]
    return json.dumps(payload, ensure_ascii=False)


def _post(path: str, json_body: dict[str, Any]) -> str:
    url = f"{_base_url()}{path}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(url, json=json_body)
    except httpx.RequestError as e:
        logger.exception("ener-vault POST failed: %s", url)
        return json.dumps({"ok": False, "error": str(e), "url": url}, ensure_ascii=False)
    payload: dict[str, Any] = {"ok": r.is_success, "status_code": r.status_code, "url": url}
    try:
        payload["body"] = r.json()
    except Exception:
        payload["body"] = r.text[:4096]
    return json.dumps(payload, ensure_ascii=False)


@tool
def ener_vault_check_health() -> str:
    """Check whether ener-vault is up (GET /health). Returns JSON with status."""
    return _get("/health")


@tool
def ener_vault_list_devices(page: int = 0, size: int = 20) -> str:
    """List devices registered in ener-vault with pagination (GET /v1/devices)."""
    return _get("/v1/devices", params={"page": page, "size": size})


@tool
def ener_vault_get_device(device_id: str) -> str:
    """Get one device by UUID (GET /v1/devices/{device_id})."""
    did = device_id.strip()
    return _get(f"/v1/devices/{did}")


@tool
def ener_vault_create_device(
    name: str | None = None,
    serial_number: str | None = None,
    is_active: bool = True,
    device_id: str | None = None,
) -> str:
    """Create a new energy meter (medidor) in ener-vault.

    POST /v1/devices. Use at least a descriptive name and/or serial_number; serial_number must be
    unique. On duplicate serial or duplicate id, the API returns 409. Successful creation returns
    201 with id, timestamps, etc.

    Optional ``device_id``: UUID string for the meter primary key. If omitted, ener-vault assigns
    a server-generated UUID (version 1).
    """
    body: dict[str, Any] = {"is_active": is_active}
    if device_id is not None and device_id.strip():
        body["id"] = device_id.strip()
    if name is not None and name.strip():
        body["name"] = name.strip()
    if serial_number is not None and serial_number.strip():
        body["serial_number"] = serial_number.strip()
    return _post("/v1/devices", body)


@tool
def ener_vault_query_entities(
    entity_id: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """List or fetch one catalog entity (tipo de carga) in ener-vault.

    Entities are the catalog rows used to assign meters (devices) over time windows.
    If ``entity_id`` is set, GET /v1/entities/{entity_id}; otherwise GET /v1/entities with pagination.
    """
    if entity_id is not None and entity_id.strip():
        return _get(f"/v1/entities/{entity_id.strip()}")
    return _get("/v1/entities", params={"page": page, "size": size})


@tool
def ener_vault_create_device_entity_assignment(
    device_id: str,
    entity_id: str,
    started_at: str,
    ended_at: str | None = None,
    description: str | None = None,
) -> str:
    """Link a meter (device) to an entity for a time range (POST /v1/device-entity-assignments).

    Use UUIDs from ener-vault for device_id and entity_id (list devices / query entities first).
    ``started_at`` and optional ``ended_at`` must be ISO-8601 datetimes, e.g. 2025-04-18T12:00:00Z
    or 2025-04-18T14:00:00+00:00. If ``ended_at`` is omitted, the assignment is open-ended.
    """
    body: dict[str, Any] = {
        "device_id": device_id.strip(),
        "entity_id": entity_id.strip(),
        "started_at": started_at.strip(),
    }
    if ended_at is not None and ended_at.strip():
        body["ended_at"] = ended_at.strip()
    if description is not None and description.strip():
        body["description"] = description.strip()
    return _post("/v1/device-entity-assignments", body)


TOOLS_ENER_VAULT: list[BaseTool] = [
    ener_vault_check_health,
    ener_vault_list_devices,
    ener_vault_get_device,
    ener_vault_create_device,
    ener_vault_query_entities,
    ener_vault_create_device_entity_assignment,
]
