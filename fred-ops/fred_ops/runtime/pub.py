from __future__ import annotations

import logging
from typing import Callable

from pydantic import BaseModel

from fred_ops.config import FredOpsConfig
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)


async def run_pub(
    config: FredOpsConfig,
    execute_fn: Callable,
    OutputModel: type[BaseModel],
) -> None:
    client = await connect_broker(config.broker)
    async with client:
        while True:
            try:
                result = await execute_fn(OutputModel, **config.kwargs)
                await client.publish(config.output.topic, result.model_dump_json())
            except Exception:
                # PUB mode has no incoming message to skip — fail fast so the
                # process exits rather than silently spinning in a broken state.
                logger.exception("execute raised an exception, stopping")
                raise
