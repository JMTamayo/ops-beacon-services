from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiomqtt

from fred_ops.config import BrokerConfig

logger = logging.getLogger(__name__)


async def connect_broker(config: BrokerConfig) -> aiomqtt.Client:
    """
    Connect to MQTT broker with comprehensive logging.

    Logs broker configuration before attempting connection, success with timing,
    and detailed errors if connection fails. Fails fast on error (no retries).

    Args:
        config: BrokerConfig with host, port, username, password, client_id

    Returns:
        Connected aiomqtt.Client instance

    Raises:
        Propagates connection exceptions from aiomqtt
    """
    # Log configuration before attempting connection
    auth_status = "activada" if config.username else "desactivada"
    logger.info(
        f"Conectando a Broker MQTT: host={config.host}, port={config.port}, "
        f"client_id={config.client_id}, protocol=v3.1.1, autenticación={auth_status}"
    )

    start_time = time.perf_counter()

    try:
        # Create MQTT client with connection parameters
        client = aiomqtt.Client(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            identifier=config.client_id,
            protocol_version=aiomqtt.ProtocolVersion.V311,
        )

        # Enter async context to establish connection
        await client.__aenter__()

        # Log successful connection with timing
        duration = time.perf_counter() - start_time
        logger.info(
            f"✓ Conexión al Broker MQTT establecida (duración: {duration:.2f}s)"
        )

        return client

    except Exception as e:
        # Log error with context and re-raise (fail fast)
        error_type = type(e).__name__
        logger.error(
            f"✗ Error al conectar a Broker MQTT en {config.host}:{config.port} "
            f"— {error_type}: {str(e)}"
        )
        raise
