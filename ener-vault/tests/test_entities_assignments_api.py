from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

from tests.conftest import TEST_DEVICE_ID


def _first_seed_entity_id() -> uuid.UUID:
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / "config" / ".env")
    url = os.environ.get("DATABASE_URL")
    assert url, "DATABASE_URL required"
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM energy_meters.entities ORDER BY created_at LIMIT 1")
            ).one()
            return uuid.UUID(str(row[0]))
    finally:
        engine.dispose()


def test_entities_crud_and_delete_blocked_by_assignment(client: TestClient) -> None:
    suffix = uuid.uuid4().hex[:8]
    created = client.post("/v1/entities", json={"name": f"Test entity {suffix}"})
    assert created.status_code == 201, created.text
    body = created.json()
    eid = uuid.UUID(body["id"])
    assert body["name"] == f"Test entity {suffix}"
    assert "updated_at" in body

    got = client.get(f"/v1/entities/{eid}")
    assert got.status_code == 200

    listed = client.get("/v1/entities", params={"page": 0, "size": 5})
    assert listed.status_code == 200
    payload = listed.json()
    assert "items" in payload
    assert payload["page"] == 0
    assert payload["size"] == 5

    patched = client.patch(f"/v1/entities/{eid}", json={"name": f"Renamed {suffix}"})
    assert patched.status_code == 200
    assert patched.json()["name"] == f"Renamed {suffix}"

    assign = client.post(
        "/v1/device-entity-assignments",
        json={
            "device_id": str(TEST_DEVICE_ID),
            "entity_id": str(eid),
            "started_at": "2026-01-01T00:00:00+00:00",
            "description": "integration test assignment",
        },
    )
    assert assign.status_code == 201, assign.text
    aid = uuid.UUID(assign.json()["id"])

    blocked = client.delete(f"/v1/entities/{eid}")
    assert blocked.status_code == 409

    assert client.delete(f"/v1/device-entity-assignments/{aid}").status_code == 204
    assert client.delete(f"/v1/entities/{eid}").status_code == 204
    assert client.get(f"/v1/entities/{eid}").status_code == 404


def test_assignments_overlap_conflict(client: TestClient) -> None:
    eid = _first_seed_entity_id()
    start = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    first = client.post(
        "/v1/device-entity-assignments",
        json={
            "device_id": str(TEST_DEVICE_ID),
            "entity_id": str(eid),
            "started_at": start.isoformat(),
            "ended_at": (start + timedelta(hours=2)).isoformat(),
        },
    )
    assert first.status_code == 201, first.text
    aid = uuid.UUID(first.json()["id"])

    overlap = client.post(
        "/v1/device-entity-assignments",
        json={
            "device_id": str(TEST_DEVICE_ID),
            "entity_id": str(eid),
            "started_at": (start + timedelta(hours=1)).isoformat(),
            "ended_at": (start + timedelta(hours=3)).isoformat(),
        },
    )
    assert overlap.status_code == 409

    assert client.delete(f"/v1/device-entity-assignments/{aid}").status_code == 204


def test_assignments_list_description_like(client: TestClient) -> None:
    eid = _first_seed_entity_id()
    token = uuid.uuid4().hex[:10]
    r = client.post(
        "/v1/device-entity-assignments",
        json={
            "device_id": str(TEST_DEVICE_ID),
            "entity_id": str(eid),
            "started_at": "2026-05-10T10:00:00+00:00",
            "description": f"Desk lamp {token} office corner",
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    listed = client.get(
        "/v1/device-entity-assignments",
        params={
            "device_id": str(TEST_DEVICE_ID),
            "description_like": token.upper(),
            "page": 0,
            "size": 50,
        },
    )
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()["items"]}
    assert aid in ids

    assert client.delete(f"/v1/device-entity-assignments/{aid}").status_code == 204


def test_measurement_patch_sets_updated_at(client: TestClient, test_device_id: uuid.UUID) -> None:
    created = client.post(
        "/v1/measurements",
        json={
            "device_id": str(test_device_id),
            "local_time": "2026-04-20T10:00:00+00:00",
            "voltage": 120.0,
            "current": 1.0,
            "active_power": 100.0,
            "active_energy": 50.0,
            "frequency": 60.0,
            "power_factor": 1.0,
        },
    )
    assert created.status_code == 201, created.text
    mid = created.json()["id"]
    assert created.json().get("updated_at") in (None,)

    patched = client.patch(f"/v1/measurements/{mid}", json={"voltage": 121.0})
    assert patched.status_code == 200
    assert patched.json()["updated_at"] is not None

    assert client.delete(f"/v1/measurements/{mid}").status_code == 204
