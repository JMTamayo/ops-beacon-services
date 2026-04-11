from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class DashboardSink:
    """Append-only SQLite store for dashboard charts (WAL, single-writer lock)."""

    def __init__(self, sqlite_path: str, max_rows: int) -> None:
        self._path = sqlite_path
        self._max_rows = max_rows
        self._lock = threading.Lock()
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    mode TEXT NOT NULL,
                    input_json TEXT,
                    output_json TEXT,
                    meta_json TEXT
                )
                """
            )
            conn.commit()

    def record(
        self,
        *,
        mode: str,
        input_payload: dict[str, Any] | None = None,
        output_payload: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        ts = time.time()
        in_j = json.dumps(input_payload) if input_payload is not None else None
        out_j = json.dumps(output_payload) if output_payload is not None else None
        meta_j = json.dumps(meta) if meta is not None else None
        with self._lock:
            with sqlite3.connect(self._path, check_same_thread=False) as conn:
                conn.execute(
                    "INSERT INTO events (ts, mode, input_json, output_json, meta_json) VALUES (?, ?, ?, ?, ?)",
                    (ts, mode, in_j, out_j, meta_j),
                )
                self._prune(conn)
                conn.commit()

    def _prune(self, conn: sqlite3.Connection) -> None:
        cur = conn.execute("SELECT COUNT(*) FROM events")
        count = cur.fetchone()[0]
        if count <= self._max_rows:
            return
        to_delete = count - self._max_rows
        conn.execute(
            "DELETE FROM events WHERE id IN (SELECT id FROM events ORDER BY id ASC LIMIT ?)",
            (to_delete,),
        )

    @staticmethod
    def default_sqlite_path() -> str:
        return str(Path.cwd() / ".fred-ops-dashboard.db")
