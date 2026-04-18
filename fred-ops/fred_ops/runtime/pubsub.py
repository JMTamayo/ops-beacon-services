from __future__ import annotations

import json
import logging
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig
from fred_ops.dashboard.recorder import maybe_record_dashboard
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)


async def run_pubsub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
    OutputModel: type[BaseModel],
    storage_fn: Callable[..., Any] | None = None,
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
                maybe_record_dashboard(
                    config,
                    input_payload=input_obj.model_dump(),
                    output_payload=result.model_dump(),
                    meta=None,
                )
                if storage_fn is not None:
                    try:
                        await storage_fn(input_obj, result, **config.kwargs)
                    except Exception:
                        logger.exception("storage raised an exception, continuing")
            except Exception:
                logger.exception("execute raised an exception, skipping message")
