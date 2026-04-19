from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiomqtt

from fred_ops.config import BrokerConfig

logger = logging.getLogger(__name__)


class BrokerReconnectExhausted(Exception):
    """Raised when the broker could not be reached after ``reconnect_max_attempts`` failures in a row."""


_RECONNECTABLE_ERRORS: tuple[type[BaseException], ...] = (
    aiomqtt.MqttError,
    ConnectionError,
    TimeoutError,
    OSError,
)


async def run_mqtt_session_with_reconnect(
    broker: BrokerConfig,
    connected_work: Callable[[aiomqtt.Client, Callable[[], None]], Awaitable[None]],
) -> None:
    """
    Connect, run ``connected_work(client, on_session_ready)`` inside ``async with client``,
    and on transport failures retry until ``reconnect_max_attempts`` failures occur without
    resetting the counter. Call ``on_session_ready()`` after a successful subscribe (or
    publish in pub mode) so each **fully recovered** session clears the failure streak.

    If ``connected_work`` returns without raising (e.g. finite test iterator), the loop ends.
    """
    consecutive_failures = 0

    def on_session_ready() -> None:
        nonlocal consecutive_failures
        consecutive_failures = 0

    while True:
        try:
            client = await connect_broker(broker)
            async with client:
                await connected_work(client, on_session_ready)
            return
        except asyncio.CancelledError:
            raise
        except _RECONNECTABLE_ERRORS as e:
            consecutive_failures += 1
            logger.warning(
                "MQTT connection or session lost (%s/%s; counter resets after a successful "
                "subscribe or publish): %s: %s",
                consecutive_failures,
                broker.reconnect_max_attempts,
                type(e).__name__,
                e,
            )
            if consecutive_failures >= broker.reconnect_max_attempts:
                msg = (
                    f"Could not restore MQTT connection after {broker.reconnect_max_attempts} "
                    f"consecutive failures without a healthy session (last error: {e})"
                )
                logger.error(msg)
                raise BrokerReconnectExhausted(msg) from e
            await asyncio.sleep(broker.reconnect_delay_seconds)


async def connect_broker(config: BrokerConfig) -> aiomqtt.Client:
    """
    Create MQTT client with connection verification and logging.

    Logs broker configuration before attempting, success with timing,
    and detailed errors if connection fails. Fails fast on error.

    The returned client is ready for use with async context manager.

    Args:
        config: BrokerConfig with host, port, username, password, client_id

    Returns:
        Verified aiomqtt.Client instance ready for use with async with

    Raises:
        Propagates connection exceptions from aiomqtt
    """
    auth_status = "enabled" if config.username else "disabled"
    logger.info(
        "Connecting to MQTT broker: host=%s, port=%s, client_id=%s, protocol=MQTTv3.1.1, "
        "authentication=%s",
        config.host,
        config.port,
        config.client_id,
        auth_status,
    )

    start_time = time.perf_counter()

    try:
        # Verify connection by entering context with test client
        test_client = aiomqtt.Client(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            identifier=config.client_id,
            protocol=aiomqtt.ProtocolVersion.V311,
        )

        async with test_client:
            pass  # Connection successful, exit cleanly

        # Log successful connection with timing
        duration = time.perf_counter() - start_time
        logger.info("MQTT broker connection established (%.2fs)", duration)

        # Return a new client for the caller to use with async with
        return aiomqtt.Client(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            identifier=config.client_id,
            protocol=aiomqtt.ProtocolVersion.V311,
        )

    except Exception as e:
        # Log error with context and re-raise (fail fast)
        error_type = type(e).__name__
        logger.error(
            "Failed to connect to MQTT broker at %s:%s — %s: %s",
            config.host,
            config.port,
            error_type,
            e,
        )
        raise
