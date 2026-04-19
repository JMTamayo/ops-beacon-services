from __future__ import annotations

import logging
import os
import sys

# Single format for ``fred-ops run`` (framework + user script loggers).
DEFAULT_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _level_from_env() -> int:
    name = os.environ.get("FRED_OPS_LOG_LEVEL", "INFO").upper()
    return getattr(logging, name, logging.INFO)


def configure_logging(level: int | None = None) -> None:
    """
    Configure the root logger once so fred-ops and the user processor share the same format.

    Skips if handlers are already attached (e.g. pytest, or a host that configured logging).
    Level: ``level`` argument, else ``FRED_OPS_LOG_LEVEL`` (default INFO).
    """
    root = logging.getLogger()
    if root.handlers:
        if level is not None:
            root.setLevel(level)
        else:
            root.setLevel(_level_from_env())
        return

    fmt = os.environ.get("FRED_OPS_LOG_FORMAT", DEFAULT_LOG_FORMAT)
    datefmt = os.environ.get("FRED_OPS_LOG_DATE_FORMAT", DEFAULT_DATE_FORMAT)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt))
    root.setLevel(level if level is not None else _level_from_env())
    root.addHandler(handler)
