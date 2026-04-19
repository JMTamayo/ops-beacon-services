import pytest
from unittest.mock import AsyncMock, patch

import aiomqtt

from fred_ops.config import BrokerConfig
from fred_ops.runtime.broker import BrokerReconnectExhausted, run_mqtt_session_with_reconnect


@pytest.mark.asyncio
async def test_run_mqtt_session_exhausts_when_session_never_ready():
    broker = BrokerConfig(
        host="localhost",
        port=1883,
        reconnect_max_attempts=2,
        reconnect_delay_seconds=0,
    )
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "fred_ops.runtime.broker.connect_broker",
        new_callable=AsyncMock,
        return_value=mock_client,
    ) as mock_connect:

        async def work(_client, _on_ready):
            raise aiomqtt.MqttError("simulated disconnect")

        with pytest.raises(BrokerReconnectExhausted):
            await run_mqtt_session_with_reconnect(broker, work)

    assert mock_connect.call_count == 2


@pytest.mark.asyncio
async def test_run_mqtt_session_recovers_after_failed_attempt():
    broker = BrokerConfig(
        host="localhost",
        port=1883,
        reconnect_max_attempts=5,
        reconnect_delay_seconds=0,
    )
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    attempt = 0

    with patch(
        "fred_ops.runtime.broker.connect_broker",
        new_callable=AsyncMock,
        return_value=mock_client,
    ) as mock_connect:

        async def work(_client, on_ready):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise aiomqtt.MqttError("first disconnect")
            on_ready()
            return

        await run_mqtt_session_with_reconnect(broker, work)

    assert mock_connect.call_count == 2
    assert attempt == 2
