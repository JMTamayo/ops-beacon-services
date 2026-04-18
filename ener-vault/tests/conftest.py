"""Integration tests touch a real PostgreSQL database from DATABASE_URL.

Only rows with ``TEST_DEVICE_ID`` are removed before and after each test so
other data in the same database is preserved.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from starlette.testclient import TestClient

load_dotenv(Path(__file__).resolve().parent.parent / "config" / ".env")

# Fixed UUID: all test-created measurements must use this device_id so cleanup can target them.
TEST_DEVICE_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")


def _reset_test_device_catalog() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set; skipping integration tests")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM energy_meters.device_entity_assignments "
                    "WHERE device_id = CAST(:id AS uuid)"
                ),
                {"id": str(TEST_DEVICE_ID)},
            )
            conn.execute(
                text(
                    "DELETE FROM energy_meters.measurements "
                    "WHERE device_id = CAST(:id AS uuid)"
                ),
                {"id": str(TEST_DEVICE_ID)},
            )
            conn.execute(
                text("DELETE FROM energy_meters.devices WHERE id = CAST(:id AS uuid)"),
                {"id": str(TEST_DEVICE_ID)},
            )
            conn.execute(
                text(
                    "INSERT INTO energy_meters.devices (id, created_at, is_active) "
                    "VALUES (CAST(:id AS uuid), now(), true)"
                ),
                {"id": str(TEST_DEVICE_ID)},
            )
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_test_measurements() -> Generator[None, None, None]:
    _reset_test_device_catalog()
    yield
    _reset_test_device_catalog()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    # Import after env is configured (e.g. via shell or config/.env picked up by Settings).
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_device_id() -> uuid.UUID:
    return TEST_DEVICE_ID
