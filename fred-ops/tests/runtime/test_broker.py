import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fred_ops.config import BrokerConfig
from fred_ops.runtime.broker import connect_broker


@pytest.mark.asyncio
async def test_connect_broker_success():
    """Test successful connection to MQTT broker with logging."""
    broker_config = BrokerConfig(
        host="localhost",
        port=1883,
        username=None,
        password=None,
        client_id="test-client"
    )

    # Mock aiomqtt.Client to avoid actual connection
    with patch("fred_ops.runtime.broker.aiomqtt.Client") as mock_client_class:
        # Create separate instances for test_client and returned client
        test_client = AsyncMock()
        return_client = AsyncMock()
        mock_client_class.side_effect = [test_client, return_client]

        result = await connect_broker(broker_config)

        # Verify the client was created with correct parameters
        assert mock_client_class.call_count == 2  # Called twice: once for test, once for return

        # Verify that the test client was properly used with async with
        # __aenter__ and __aexit__ should have been called on the test client
        test_client.__aenter__.assert_called_once()
        test_client.__aexit__.assert_called_once()

        # The returned client is a different instance (second call)
        assert result is return_client
        assert result is not test_client


@pytest.mark.asyncio
async def test_connect_broker_logs_configuration():
    """Test that connect_broker logs the broker configuration before connecting."""
    broker_config = BrokerConfig(
        host="broker.example.com",
        port=8883,
        username="user",
        password="secret",
        client_id="fred-ops-abc123"
    )

    with patch("fred_ops.runtime.broker.aiomqtt.Client") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        with patch("fred_ops.runtime.broker.logger") as mock_logger:
            await connect_broker(broker_config)

            # Verify configuration was logged
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args_list[0][0][0]
            assert "broker.example.com" in call_args
            assert "8883" in call_args
            assert "fred-ops-abc123" in call_args
            assert "secret" not in call_args  # Password should never be logged


@pytest.mark.asyncio
async def test_connect_broker_logs_success():
    """Test that connect_broker logs success message with connection duration."""
    broker_config = BrokerConfig(
        host="localhost",
        port=1883,
        username=None,
        password=None,
        client_id="test-client"
    )

    with patch("fred_ops.runtime.broker.aiomqtt.Client") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        with patch("fred_ops.runtime.broker.logger") as mock_logger:
            with patch("fred_ops.runtime.broker.time") as mock_time:
                # Mock time to return predictable values
                mock_time.perf_counter.side_effect = [0.0, 0.24]

                await connect_broker(broker_config)

                # Verify success was logged
                success_logs = [
                    call
                    for call in mock_logger.info.call_args_list
                    if "established" in str(call) or "connection" in str(call).lower()
                ]
                assert len(success_logs) > 0
                # Verify that the success log contains the duration
                success_msg = success_logs[0][0][0]
                assert "0.24" in success_msg


@pytest.mark.asyncio
async def test_connect_broker_logs_error():
    """Test that connect_broker logs errors and re-raises exceptions."""
    broker_config = BrokerConfig(
        host="nonexistent.broker",
        port=1883,
        username=None,
        password=None,
        client_id="test-client"
    )

    with patch("fred_ops.runtime.broker.aiomqtt.Client") as mock_client_class:
        # Simulate connection error
        mock_client_class.side_effect = ConnectionRefusedError("Connection refused")

        with patch("fred_ops.runtime.broker.logger") as mock_logger:
            with pytest.raises(ConnectionRefusedError):
                await connect_broker(broker_config)

            # Verify error was logged
            assert mock_logger.error.called
            error_call = mock_logger.error.call_args_list[0][0][0]
            assert "nonexistent.broker" in error_call
            assert "1883" in error_call
