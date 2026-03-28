import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import create_model

from fred_ops.runtime.pub import run_pub
from fred_ops.config import FredOpsConfig, BrokerConfig, TopicConfig


OutputModel = create_model("OutputModel", value=(float, ...))


def make_config(**kwargs) -> FredOpsConfig:
    defaults = dict(
        broker=BrokerConfig(host="localhost", port=1883),
        mode="pub",
        output=TopicConfig(topic="out/topic", schema_={"value": "float"}),
        kwargs={},
    )
    defaults.update(kwargs)
    return FredOpsConfig(**defaults)


async def test_run_pub_calls_execute_with_output_class():
    config = make_config()
    call_count = 0

    async def execute_fn(output, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise StopAsyncIteration  # stop after 2 iterations
        return output(value=1.0)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("fred_ops.runtime.pub.aiomqtt.Client", return_value=mock_client):
        with pytest.raises(StopAsyncIteration):
            await run_pub(config, execute_fn, OutputModel)

    assert call_count == 2


async def test_run_pub_publishes_result():
    config = make_config()
    call_count = 0

    async def execute_fn(output, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise StopAsyncIteration
        return output(value=3.14)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("fred_ops.runtime.pub.aiomqtt.Client", return_value=mock_client):
        with pytest.raises(StopAsyncIteration):
            await run_pub(config, execute_fn, OutputModel)

    mock_client.publish.assert_called_with(
        "out/topic",
        OutputModel(value=3.14).model_dump_json(),
    )


async def test_run_pub_forwards_kwargs():
    config = make_config(kwargs={"interval": 0.1})
    captured_kwargs = {}

    async def execute_fn(output, **kwargs):
        captured_kwargs.update(kwargs)
        raise StopAsyncIteration

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("fred_ops.runtime.pub.aiomqtt.Client", return_value=mock_client):
        with pytest.raises(StopAsyncIteration):
            await run_pub(config, execute_fn, OutputModel)

    assert captured_kwargs["interval"] == 0.1
