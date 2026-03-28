import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import create_model

from fred_ops.runtime.sub import run_sub
from fred_ops.config import FredOpsConfig, BrokerConfig, TopicConfig


InputModel = create_model("InputModel", sensor_id=(str, ...), reading=(float, ...))


def make_config(**kwargs) -> FredOpsConfig:
    defaults = dict(
        broker=BrokerConfig(host="localhost", port=1883),
        mode="sub",
        input=TopicConfig(topic="in/topic", schema_={"sensor_id": "str", "reading": "float"}),
        kwargs={},
    )
    defaults.update(kwargs)
    return FredOpsConfig(**defaults)


@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.payload = json.dumps({"sensor_id": "s1", "reading": 9.9}).encode()
    return msg


async def test_run_sub_calls_execute_with_input(mock_message):
    config = make_config()
    execute_fn = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.sub.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    execute_fn.assert_called_once()
    args = execute_fn.call_args
    assert isinstance(args[0][0], InputModel)
    assert args[0][0].sensor_id == "s1"
    assert args[0][0].reading == 9.9


async def test_run_sub_does_not_publish(mock_message):
    config = make_config()
    execute_fn = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.sub.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    mock_client.publish.assert_not_called()


async def test_run_sub_forwards_kwargs(mock_message):
    config = make_config(kwargs={"alert_level": "high"})
    captured = {}

    async def execute_fn(input, **kwargs):
        captured.update(kwargs)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.sub.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    assert captured["alert_level"] == "high"


async def test_run_sub_skips_invalid_json():
    config = make_config()
    execute_fn = AsyncMock()

    bad_msg = MagicMock()
    bad_msg.payload = b"bad"
    good_msg = MagicMock()
    good_msg.payload = json.dumps({"sensor_id": "s2", "reading": 1.0}).encode()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([bad_msg, good_msg])

    with patch("fred_ops.runtime.sub.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    assert execute_fn.call_count == 1


async def test_run_sub_skips_validation_error(mock_message):
    """Valid JSON but wrong types should be skipped (ValidationError)."""
    bad_msg = MagicMock()
    bad_msg.payload = json.dumps({"sensor_id": "s1", "reading": "not-a-float"}).encode()

    config = make_config()
    execute_fn = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([bad_msg, mock_message])

    with patch("fred_ops.runtime.sub.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    assert execute_fn.call_count == 1


async def test_run_sub_skips_execute_exception(mock_message):
    """If execute raises, the message is skipped and the loop continues."""
    second_msg = MagicMock()
    second_msg.payload = json.dumps({"sensor_id": "s2", "reading": 5.0}).encode()

    config = make_config()
    call_count = 0

    async def execute_fn(input_obj, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("something went wrong")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message, second_msg])

    with patch("fred_ops.runtime.sub.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    assert call_count == 2


async def _async_iter(items):
    for item in items:
        yield item
