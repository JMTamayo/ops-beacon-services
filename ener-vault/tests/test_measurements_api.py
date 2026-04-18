from __future__ import annotations

import uuid

from starlette.testclient import TestClient


def _sample_payload(device_id: uuid.UUID, *, local_time: str) -> dict:
    return {
        "device_id": str(device_id),
        "local_time": local_time,
        "voltage": 120.5,
        "current": 2.1,
        "active_power": 250.0,
        "active_energy": 1000.0,
        "frequency": 60.0,
        "power_factor": 0.95,
    }


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_measurements_crud_roundtrip(client: TestClient, test_device_id: uuid.UUID) -> None:
    created = client.post(
        "/v1/measurements",
        json=_sample_payload(test_device_id, local_time="2026-04-18T12:00:00+00:00"),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    mid = uuid.UUID(body["id"])
    assert body["device_id"] == str(test_device_id)

    got = client.get(f"/v1/measurements/{mid}")
    assert got.status_code == 200
    assert got.json()["id"] == str(mid)

    listed = client.get("/v1/measurements", params={"device_id": str(test_device_id)})
    assert listed.status_code == 200
    payload = listed.json()
    assert "items" in payload
    assert payload["total"] >= 1
    assert len(payload["items"]) >= 1

    patched = client.patch(
        f"/v1/measurements/{mid}",
        json={"voltage": 121.0},
    )
    assert patched.status_code == 200
    assert patched.json()["voltage"] == 121.0

    deleted = client.delete(f"/v1/measurements/{mid}")
    assert deleted.status_code == 204

    missing = client.get(f"/v1/measurements/{mid}")
    assert missing.status_code == 404


def test_measurements_duplicate_device_local_time_conflict(
    client: TestClient, test_device_id: uuid.UUID
) -> None:
    payload = _sample_payload(test_device_id, local_time="2026-05-01T10:00:00+00:00")
    first = client.post("/v1/measurements", json=payload)
    assert first.status_code == 201, first.text
    second = client.post("/v1/measurements", json=payload)
    assert second.status_code == 409
    # Remove the row so duplicate test does not rely only on autouse (autouse also runs after).
    mid = uuid.UUID(first.json()["id"])
    assert client.delete(f"/v1/measurements/{mid}").status_code == 204


def test_measurements_list_filter_by_date_range(client: TestClient, test_device_id: uuid.UUID) -> None:
    r = client.post(
        "/v1/measurements",
        json=_sample_payload(test_device_id, local_time="2026-06-15T08:30:00+00:00"),
    )
    assert r.status_code == 201, r.text

    listed = client.get(
        "/v1/measurements",
        params={
            "device_id": str(test_device_id),
            "local_time_from": "2026-06-15T00:00:00+00:00",
            "local_time_to": "2026-06-15T23:59:59+00:00",
        },
    )
    assert listed.status_code == 200
    body = listed.json()
    rows = body["items"]
    assert body["total"] >= 1
    assert len(rows) >= 1
    assert all(row["device_id"] == str(test_device_id) for row in rows)

    for row in rows:
        assert client.delete(f"/v1/measurements/{row['id']}").status_code == 204


def test_create_measurement_requires_catalog_device(client: TestClient) -> None:
    missing = uuid.UUID("aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee")
    r = client.post(
        "/v1/measurements",
        json=_sample_payload(missing, local_time="2026-08-01T10:00:00+00:00"),
    )
    assert r.status_code == 404


def test_measurements_list_page_and_size_query_params(client: TestClient) -> None:
    r = client.get("/v1/measurements", params={"page": 0, "size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 0
    assert body["size"] == 10
    assert "items" in body


def test_devices_list_page_and_size_query_params(client: TestClient) -> None:
    r = client.get("/v1/devices", params={"page": 0, "size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 0
    assert body["size"] == 10
    assert "items" in body


def test_entities_list_page_and_size_query_params(client: TestClient) -> None:
    r = client.get("/v1/entities", params={"page": 0, "size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 0
    assert body["size"] == 10
    assert "items" in body


def test_list_endpoints_accept_sort_date_and_order(client: TestClient) -> None:
    cases = [
        ("/v1/devices", {"sort_date": "created_at", "sort_order": "asc"}),
        ("/v1/entities", {"sort_date": "updated_at", "sort_order": "desc"}),
        ("/v1/measurements", {"sort_date": "local_time", "sort_order": "asc"}),
        ("/v1/device-entity-assignments", {"sort_date": "started_at", "sort_order": "desc"}),
    ]
    for path, extra in cases:
        r = client.get(path, params={"page": 0, "size": 5, **extra})
        assert r.status_code == 200, (path, r.text)


def test_devices_list_negative_page_validation(client: TestClient) -> None:
    r = client.get("/v1/devices", params={"page": -1, "size": 10})
    assert r.status_code == 422


def test_entities_list_negative_page_validation(client: TestClient) -> None:
    r = client.get("/v1/entities", params={"page": -1, "size": 10})
    assert r.status_code == 422


def test_measurements_list_negative_page_validation(client: TestClient) -> None:
    r = client.get("/v1/measurements", params={"page": -1, "size": 10})
    assert r.status_code == 422


def test_measurements_list_invalid_date_range_returns_400(client: TestClient) -> None:
    r = client.get(
        "/v1/measurements",
        params={
            "local_time_from": "2026-07-01T12:00:00+00:00",
            "local_time_to": "2026-07-01T08:00:00+00:00",
        },
    )
    assert r.status_code == 400
