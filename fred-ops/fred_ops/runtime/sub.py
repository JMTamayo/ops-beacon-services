from __future__ import annotations

import json
import logging
from typing import Callable

import aiomqtt
from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig

logger = logging.getLogger(__name__)


async def run_sub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
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
        await client.subscribe(config.input.topic)
        async for message in client.messages:
            try:
                payload = json.loads(message.payload)
                input_obj = InputModel(**payload)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning("Skipping malformed message: %s", e)
                continue
            try:
                await execute_fn(input_obj, **config.kwargs)
            except Exception:
                logger.exception("execute raised an exception, skipping message")
                continue
