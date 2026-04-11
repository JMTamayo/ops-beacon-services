from __future__ import annotations

import json
import logging
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig
from fred_ops.dashboard.recorder import maybe_record_dashboard
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)


async def run_sub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel] | None,
    storage_fn: Callable[..., Any] | None = None,
) -> None:
    if config.input is not None and config.input.generic_event_log:
        await _run_sub_generic_event_log(config, execute_fn, storage_fn)
        return

    if InputModel is None:
        raise RuntimeError("InputModel is required when generic_event_log is false")

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
                await execute_fn(input_obj, **config.kwargs)
                maybe_record_dashboard(
                    config,
                    input_payload=input_obj.model_dump(),
                    output_payload=None,
                    meta=None,
                )
                if storage_fn is not None:
                    try:
                        await storage_fn(input_obj, **config.kwargs)
                    except Exception:
                        logger.exception("storage raised an exception, skipping message")
                        continue
            except Exception:
                logger.exception("execute raised an exception, skipping message")
                continue


async def _run_sub_generic_event_log(
    config: FredOpsConfig,
    execute_fn: Callable[..., Any],
    storage_fn: Callable[..., Any] | None = None,
) -> None:
    """Subscribe and forward each message with mqtt_topic, payload_json, payload_bytes."""
    client = await connect_broker(config.broker)
    async with client:
        await client.subscribe(config.input.topic)
        logger.info(
            "generic_event_log: subscribed to topic=%s",
            config.input.topic,
        )
        async for message in client.messages:
            raw: bytes = message.payload if message.payload else b""
            topic_str = str(message.topic)
            payload_json: Any | None
            if not raw:
                payload_json = None
            else:
                try:
                    payload_json = json.loads(raw)
                except json.JSONDecodeError:
                    payload_json = {
                        "_raw_text": raw.decode("utf-8", errors="replace"),
                    }
                    logger.debug(
                        "Non-JSON payload on topic=%s; wrapping as _raw_text",
                        topic_str,
                    )
            try:
                await execute_fn(
                    mqtt_topic=topic_str,
                    payload_json=payload_json,
                    payload_bytes=raw if raw else None,
                    **config.kwargs,
                )
                in_payload: dict | None
                if isinstance(payload_json, dict):
                    in_payload = payload_json
                elif payload_json is None:
                    in_payload = None
                else:
                    in_payload = {"_value": payload_json}
                maybe_record_dashboard(
                    config,
                    input_payload=in_payload,
                    output_payload=None,
                    meta={"mqtt_topic": topic_str},
                )
                if storage_fn is not None:
                    try:
                        await storage_fn(
                            mqtt_topic=topic_str,
                            payload_json=payload_json,
                            payload_bytes=raw if raw else None,
                            **config.kwargs,
                        )
                    except Exception:
                        logger.exception(
                            "storage raised an exception (topic=%s), skipping message",
                            topic_str,
                        )
                        continue
            except Exception:
                logger.exception(
                    "execute raised an exception (topic=%s), skipping message",
                    topic_str,
                )
                continue
