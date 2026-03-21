from __future__ import annotations

import logging
import os

import uvicorn

from bot_telegram.presentation.app import build_app, create_app
from bot_telegram.presentation.bootstrap import load_runtime_config

_log_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(level=_log_level, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    config = load_runtime_config()
    app = build_app(config)
    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
        log_level="info",
    )


# Uvicorn: `uvicorn bot_telegram.presentation.main:app`
app = create_app()


if __name__ == "__main__":
    main()
