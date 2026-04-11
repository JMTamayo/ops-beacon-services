from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fred_ops.config import FredOpsConfig
from fred_ops.dashboard.sink import DashboardSink

logger = logging.getLogger(__name__)

_sink: DashboardSink | None = None


def init_dashboard_recorder(config: FredOpsConfig) -> None:
    """Create SQLite sink when dashboard is enabled (call once before run_*)."""
    global _sink
    if config.dashboard is None or not config.dashboard.enabled:
        _sink = None
        return
    path = config.dashboard.sqlite_path or DashboardSink.default_sqlite_path()
    path = str(Path(path).resolve())
    _sink = DashboardSink(path, max_rows=config.dashboard.max_rows)
    os.environ["FRED_OPS_SQLITE_PATH"] = path


def maybe_record_dashboard(
    config: FredOpsConfig,
    *,
    input_payload: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if _sink is None:
        return
    try:
        _sink.record(
            mode=config.mode,
            input_payload=input_payload,
            output_payload=output_payload,
            meta=meta,
        )
    except Exception:
        logger.exception("dashboard record failed, continuing")
