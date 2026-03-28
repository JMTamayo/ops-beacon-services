from __future__ import annotations

import json
import logging
from typing import Callable

from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)


async def run_pubsub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
    OutputModel: type[BaseModel],
) -> None:
    client = await connect_broker(config.broker)
    async with client:
        await client.subscribe(config.input.topic)
        async for message in client.messages:
            try:
                payload = json.loads(message.payload)
                input_obj = InputModel(**payload)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning("Skipping malformed message: %s", e)
                continue
            try:
                result = await execute_fn(input_obj, OutputModel, **config.kwargs)
                await client.publish(config.output.topic, result.model_dump_json())
            except Exception:
                logger.exception("execute raised an exception, skipping message")
