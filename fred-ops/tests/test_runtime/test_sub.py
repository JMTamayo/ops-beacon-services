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

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
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

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    mock_client.publish.assert_not_called()


async def test_run_sub_calls_storage_after_execute(mock_message):
    config = make_config()
    sequence: list[str] = []

    async def execute_fn(input_obj, **kwargs):
        sequence.append("execute")

    async def storage_fn(input_obj, **kwargs):
        sequence.append("storage")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel, storage_fn)

    assert sequence == ["execute", "storage"]


async def test_run_sub_forwards_kwargs(mock_message):
    config = make_config(kwargs={"alert_level": "high"})
    captured = {}

    async def execute_fn(input, **kwargs):
        captured.update(kwargs)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
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

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
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

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
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

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, InputModel)

    assert call_count == 2


async def _async_iter(items):
    for item in items:
        yield item


def make_generic_config(**kwargs) -> FredOpsConfig:
    defaults = dict(
        broker=BrokerConfig(host="localhost", port=1883),
        mode="sub",
        input=TopicConfig(topic="ops-beacon/#", generic_event_log=True),
        kwargs={},
    )
    defaults.update(kwargs)
    return FredOpsConfig(**defaults)


async def test_run_sub_generic_calls_storage_after_execute():
    config = make_generic_config()
    sequence: list[str] = []

    async def execute_fn(**kwargs):
        sequence.append("execute")

    async def storage_fn(**kwargs):
        sequence.append("storage")

    mock_message = MagicMock()
    mock_message.topic = "ops-beacon/device/1"
    mock_message.payload = json.dumps({"level": "INFO"}).encode()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, None, storage_fn)

    assert sequence == ["execute", "storage"]


async def test_run_sub_generic_passes_topic_and_json():
    config = make_generic_config()
    execute_fn = AsyncMock()

    mock_message = MagicMock()
    mock_message.topic = "ops-beacon/device/1"
    mock_message.payload = json.dumps({"level": "INFO", "msg": "ok"}).encode()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, None)

    execute_fn.assert_called_once()
    call = execute_fn.call_args
    assert call.kwargs["mqtt_topic"] == "ops-beacon/device/1"
    assert call.kwargs["payload_json"] == {"level": "INFO", "msg": "ok"}
    assert call.kwargs["payload_bytes"] == mock_message.payload


async def test_run_sub_generic_empty_payload():
    config = make_generic_config()
    execute_fn = AsyncMock()

    mock_message = MagicMock()
    mock_message.topic = "ops-beacon/x"
    mock_message.payload = b""

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, None)

    execute_fn.assert_called_once()
    assert execute_fn.call_args.kwargs["payload_json"] is None
    assert execute_fn.call_args.kwargs["payload_bytes"] is None


async def test_run_sub_generic_non_json_wraps_raw_text():
    config = make_generic_config()
    execute_fn = AsyncMock()

    mock_message = MagicMock()
    mock_message.topic = "ops-beacon/raw"
    mock_message.payload = b"not-json"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, None)

    execute_fn.assert_called_once()
    assert execute_fn.call_args.kwargs["payload_json"] == {"_raw_text": "not-json"}


async def test_run_sub_generic_forwards_kwargs():
    config = make_generic_config(kwargs={"region": "eu"})
    captured = {}

    async def execute_fn(**kwargs):
        captured.update(kwargs)

    mock_message = MagicMock()
    mock_message.topic = "t"
    mock_message.payload = b"{}"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_sub(config, execute_fn, None)

    assert captured["region"] == "eu"
    assert captured["mqtt_topic"] == "t"
