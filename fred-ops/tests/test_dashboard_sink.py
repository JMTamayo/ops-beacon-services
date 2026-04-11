import json
import sqlite3
from pathlib import Path

from fred_ops.dashboard.sink import DashboardSink


def test_sink_inserts_and_prunes(tmp_path: Path) -> None:
    db = tmp_path / "d.db"
    sink = DashboardSink(str(db), max_rows=3)
    for i in range(5):
        sink.record(mode="sub", input_payload={"valor": float(i)}, output_payload=None, meta=None)

    with sqlite3.connect(db) as conn:
        n = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert n == 3

    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT input_json FROM events ORDER BY id").fetchall()
    vals = [json.loads(r[0])["valor"] for r in rows]
    assert vals == [2.0, 3.0, 4.0]


def test_sink_output_and_meta(tmp_path: Path) -> None:
    db = tmp_path / "d.db"
    sink = DashboardSink(str(db), max_rows=100)
    sink.record(
        mode="pubsub",
        input_payload={"a": 1},
        output_payload={"b": 2},
        meta={"mqtt_topic": "t/1"},
    )
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT mode, input_json, output_json, meta_json FROM events"
        ).fetchone()
    assert row[0] == "pubsub"
    assert json.loads(row[1]) == {"a": 1}
    assert json.loads(row[2]) == {"b": 2}
    assert json.loads(row[3]) == {"mqtt_topic": "t/1"}
