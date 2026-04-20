"""POST /v1/devices: optional client-supplied device id (UUID)."""

from __future__ import annotations

import uuid

from starlette.testclient import TestClient


def test_create_device_without_id_autogenerates_uuid(client: TestClient) -> None:
    serial = f"serial-auto-{uuid.uuid4().hex[:16]}"
    r = client.post(
        "/v1/devices",
        json={"name": "meter auto", "serial_number": serial, "is_active": True},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body
    uuid.UUID(body["id"])  # valid UUID string
    assert body["serial_number"] == serial


def test_create_device_with_explicit_id(client: TestClient) -> None:
    fixed = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    serial = f"serial-fixed-{uuid.uuid4().hex[:16]}"
    r = client.post(
        "/v1/devices",
        json={
            "id": str(fixed),
            "name": "meter fixed",
            "serial_number": serial,
            "is_active": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == str(fixed)
    assert body["serial_number"] == serial


def test_create_device_duplicate_id_returns_409(client: TestClient) -> None:
    fixed = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    serial_a = f"serial-dup-a-{uuid.uuid4().hex[:12]}"
    serial_b = f"serial-dup-b-{uuid.uuid4().hex[:12]}"
    first = client.post(
        "/v1/devices",
        json={
            "id": str(fixed),
            "serial_number": serial_a,
            "is_active": True,
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/v1/devices",
        json={
            "id": str(fixed),
            "serial_number": serial_b,
            "is_active": True,
        },
    )
    assert second.status_code == 409
