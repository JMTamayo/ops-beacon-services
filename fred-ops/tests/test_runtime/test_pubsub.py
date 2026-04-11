import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel, create_model

from fred_ops.runtime.pubsub import run_pubsub
from fred_ops.config import FredOpsConfig, BrokerConfig, TopicConfig


def make_config(**kwargs) -> FredOpsConfig:
    defaults = dict(
        broker=BrokerConfig(host="localhost", port=1883),
        mode="pubsub",
        input=TopicConfig(topic="in/topic", schema_={"value": "int"}),
        output=TopicConfig(topic="out/topic", schema_={"result": "str"}),
        kwargs={},
    )
    defaults.update(kwargs)
    return FredOpsConfig(**defaults)


InputModel = create_model("InputModel", value=(int, ...))
OutputModel = create_model("OutputModel", result=(str, ...))


@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.payload = json.dumps({"value": 42}).encode()
    return msg


async def test_run_pubsub_calls_execute_with_input_and_output_class(mock_message):
    config = make_config()
    execute_fn = AsyncMock(return_value=OutputModel(result="ok"))

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel)

    execute_fn.assert_called_once()
    args = execute_fn.call_args
    assert isinstance(args[0][0], InputModel)
    assert args[0][0].value == 42
    assert args[0][1] is OutputModel


async def test_run_pubsub_publishes_result(mock_message):
    config = make_config()
    execute_fn = AsyncMock(return_value=OutputModel(result="done"))

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel)

    mock_client.publish.assert_called_once_with(
        "out/topic",
        OutputModel(result="done").model_dump_json(),
    )


async def test_run_pubsub_forwards_kwargs(mock_message):
    config = make_config(kwargs={"threshold": 5.0})
    execute_fn = AsyncMock(return_value=OutputModel(result="ok"))

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel)

    _, kwargs = execute_fn.call_args
    assert kwargs["threshold"] == 5.0


async def test_run_pubsub_skips_invalid_json(mock_message):
    bad_message = MagicMock()
    bad_message.payload = b"not-json"

    config = make_config()
    execute_fn = AsyncMock(return_value=OutputModel(result="ok"))

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([bad_message, mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel)

    # Only called once — bad message was skipped
    assert execute_fn.call_count == 1


async def test_run_pubsub_skips_validation_error(mock_message):
    """Valid JSON but wrong types should be skipped (ValidationError)."""
    bad_message = MagicMock()
    bad_message.payload = json.dumps({"value": "not-an-int"}).encode()  # value should be int

    config = make_config()
    execute_fn = AsyncMock(return_value=OutputModel(result="ok"))

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([bad_message, mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel)

    # bad_message was skipped, only mock_message triggered execute
    assert execute_fn.call_count == 1


async def test_run_pubsub_calls_storage_after_publish(mock_message):
    config = make_config()
    result = OutputModel(result="done")
    execute_fn = AsyncMock(return_value=result)
    sequence: list[str] = []

    async def publish_tracked(topic: str, payload: str) -> None:
        sequence.append("publish")

    async def track_storage(*args, **kwargs) -> None:
        sequence.append("storage")

    storage_fn = AsyncMock(side_effect=track_storage)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])
    mock_client.publish = AsyncMock(side_effect=publish_tracked)

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel, storage_fn)

    assert sequence == ["publish", "storage"]
    storage_fn.assert_called_once()
    args = storage_fn.call_args[0]
    assert isinstance(args[0], InputModel)
    assert args[0].value == 42
    assert args[1] is result


async def test_run_pubsub_storage_failure_still_publishes(mock_message):
    config = make_config()
    execute_fn = AsyncMock(return_value=OutputModel(result="ok"))

    async def storage_fn(input_obj, out, **kwargs):
        raise RuntimeError("db down")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel, storage_fn)

    mock_client.publish.assert_called_once_with(
        "out/topic",
        OutputModel(result="ok").model_dump_json(),
    )


async def test_run_pubsub_skips_execute_exception(mock_message):
    """If execute raises, the message is skipped and the loop continues."""
    second_message = MagicMock()
    second_message.payload = json.dumps({"value": 99}).encode()

    config = make_config()
    call_count = 0

    async def execute_fn(input_obj, output_cls, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("something went wrong")
        return output_cls(result="recovered")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.messages = _async_iter([mock_message, second_message])

    with patch("fred_ops.runtime.broker.aiomqtt.Client", return_value=mock_client):
        await run_pubsub(config, execute_fn, InputModel, OutputModel)

    # execute was called twice — first raised, second succeeded
    assert call_count == 2
    mock_client.publish.assert_called_once_with(
        "out/topic",
        OutputModel(result="recovered").model_dump_json(),
    )


async def _async_iter(items):
    for item in items:
        yield item
