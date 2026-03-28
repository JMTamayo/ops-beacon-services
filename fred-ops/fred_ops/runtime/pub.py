from __future__ import annotations

import logging
from typing import Callable

import aiomqtt
from pydantic import BaseModel

from fred_ops.config import FredOpsConfig

logger = logging.getLogger(__name__)


async def run_pub(
    config: FredOpsConfig,
    execute_fn: Callable,
    OutputModel: type[BaseModel],
) -> None:
    broker = config.broker
    async with aiomqtt.Client(
        hostname=broker.host,
        port=broker.port,
        username=broker.username,
        password=broker.password,
        identifier=broker.client_id,
        protocol_version=aiomqtt.ProtocolVersion.V311,
    ) as client:
        while True:
            try:
                result = await execute_fn(OutputModel, **config.kwargs)
                await client.publish(config.output.topic, result.model_dump_json())
            except Exception:
                # PUB mode has no incoming message to skip — fail fast so the
                # process exits rather than silently spinning in a broken state.
                logger.exception("execute raised an exception, stopping")
                raise
