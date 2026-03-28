# Broker Connection Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a centralized MQTT broker connection helper that logs connection status, configuration details, and errors in the FredOps CLI.

**Architecture:** Create a new `broker.py` module in `fred_ops/runtime/` that encapsulates all MQTT client creation logic with comprehensive logging. This eliminates code duplication across `pub.py`, `sub.py`, and `pubsub.py`, which will be refactored to use the new helper. Connection failures will propagate immediately (fail fast).

**Tech Stack:**
- `aiomqtt` — MQTT client library
- Python `logging` module — structured logging
- `time.perf_counter()` — connection timing

---

## Task 1: Create broker.py with connect_broker function (test-first)

**Files:**
- Create: `fred_ops/runtime/broker.py`
- Create: `tests/runtime/test_broker.py`

### Step 1: Create tests directory structure

Run: `mkdir -p /Users/azrrael/Eafit/ops-beacon-services/fred-ops/tests/runtime`

Expected: Directory created

### Step 2: Write the failing test for successful connection

File: `tests/runtime/test_broker.py`

```python
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
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await connect_broker(broker_config)

        # Verify the client was created with correct parameters
        mock_client_class.assert_called_once()
        assert result == mock_client


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
                success_logs = [call for call in mock_logger.info.call_args_list
                               if "Conexión" in str(call) or "establecida" in str(call)]
                assert len(success_logs) > 0


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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/azrrael/Eafit/ops-beacon-services/fred-ops && python -m pytest tests/runtime/test_broker.py -v`

Expected: All tests FAIL (function not defined)

- [ ] **Step 4: Write minimal implementation of connect_broker**

File: `fred_ops/runtime/broker.py`

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/azrrael/Eafit/ops-beacon-services/fred-ops && python -m pytest tests/runtime/test_broker.py -v`

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add fred_ops/runtime/broker.py tests/runtime/test_broker.py
git commit -m "feat(runtime): add broker connection helper with logging"
```

---

## Task 2: Refactor pubsub.py to use connect_broker

**Files:**
- Modify: `fred_ops/runtime/pubsub.py`

- [ ] **Step 1: Read current pubsub.py to understand structure**

Current code uses:
```python
async with aiomqtt.Client(...) as client:
    await client.subscribe(config.input.topic)
    async for message in client.messages:
        # process
```

- [ ] **Step 2: Update imports in pubsub.py**

File: `fred_ops/runtime/pubsub.py`

Change from:
```python
from __future__ import annotations

import json
import logging
from typing import Callable

import aiomqtt
from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig

logger = logging.getLogger(__name__)
```

To:
```python
from __future__ import annotations

import json
import logging
from typing import Callable

from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Update run_pubsub function**

File: `fred_ops/runtime/pubsub.py`

Replace the entire `run_pubsub` function:

**Before:**
```python
async def run_pubsub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
    OutputModel: type[BaseModel],
) -> None:
    broker = config.broker
    async with aiomqtt.Client(
        hostname=broker.host,
        port=broker.port,
        username=broker.username,
        password=broker.password,
        identifier=broker.client_id,
        protocol_version=aiomqtt.ProtocolVersion.V311,
    ) as client:
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
            except Exception:
                logger.exception("execute raised an exception, skipping message")
```

**After:**
```python
async def run_pubsub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
    OutputModel: type[BaseModel],
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
            except Exception:
                logger.exception("execute raised an exception, skipping message")
```

- [ ] **Step 4: Commit**

```bash
git add fred_ops/runtime/pubsub.py
git commit -m "refactor(runtime): use connect_broker helper in pubsub mode"
```

---

## Task 3: Refactor pub.py to use connect_broker

**Files:**
- Modify: `fred_ops/runtime/pub.py`

- [ ] **Step 1: Update imports in pub.py**

File: `fred_ops/runtime/pub.py`

Change from:
```python
from __future__ import annotations

import logging
from typing import Callable

import aiomqtt
from pydantic import BaseModel

from fred_ops.config import FredOpsConfig

logger = logging.getLogger(__name__)
```

To:
```python
from __future__ import annotations

import logging
from typing import Callable

from pydantic import BaseModel

from fred_ops.config import FredOpsConfig
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Update run_pub function**

File: `fred_ops/runtime/pub.py`

Replace the entire `run_pub` function:

**Before:**
```python
async def run_pub(
    config: FredOpsConfig,
    execute_fn: Callable,
    OutputModel: type[BaseModel],
) -> None:
    broker = config.broker
    async with aiomqtt.Client(
        hostname=broker.host,
        port=broker.port,
        username=broker.username,
        password=broker.password,
        identifier=broker.client_id,
        protocol_version=aiomqtt.ProtocolVersion.V311,
    ) as client:
        while True:
            try:
                result = await execute_fn(OutputModel, **config.kwargs)
                await client.publish(config.output.topic, result.model_dump_json())
            except Exception:
                # PUB mode has no incoming message to skip — fail fast so the
                # process exits rather than silently spinning in a broken state.
                logger.exception("execute raised an exception, stopping")
                raise
```

**After:**
```python
async def run_pub(
    config: FredOpsConfig,
    execute_fn: Callable,
    OutputModel: type[BaseModel],
) -> None:
    client = await connect_broker(config.broker)
    async with client:
        while True:
            try:
                result = await execute_fn(OutputModel, **config.kwargs)
                await client.publish(config.output.topic, result.model_dump_json())
            except Exception:
                # PUB mode has no incoming message to skip — fail fast so the
                # process exits rather than silently spinning in a broken state.
                logger.exception("execute raised an exception, stopping")
                raise
```

- [ ] **Step 3: Commit**

```bash
git add fred_ops/runtime/pub.py
git commit -m "refactor(runtime): use connect_broker helper in pub mode"
```

---

## Task 4: Refactor sub.py to use connect_broker

**Files:**
- Modify: `fred_ops/runtime/sub.py`

- [ ] **Step 1: Update imports in sub.py**

File: `fred_ops/runtime/sub.py`

Change from:
```python
from __future__ import annotations

import json
import logging
from typing import Callable

import aiomqtt
from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig

logger = logging.getLogger(__name__)
```

To:
```python
from __future__ import annotations

import json
import logging
from typing import Callable

from pydantic import BaseModel, ValidationError

from fred_ops.config import FredOpsConfig
from fred_ops.runtime.broker import connect_broker

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Update run_sub function**

File: `fred_ops/runtime/sub.py`

Replace the entire `run_sub` function:

**Before:**
```python
async def run_sub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
) -> None:
    broker = config.broker
    async with aiomqtt.Client(
        hostname=broker.host,
        port=broker.port,
        username=broker.username,
        password=broker.password,
        identifier=broker.client_id,
        protocol_version=aiomqtt.ProtocolVersion.V311,
    ) as client:
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
            except Exception:
                logger.exception("execute raised an exception, skipping message")
                continue
```

**After:**
```python
async def run_sub(
    config: FredOpsConfig,
    execute_fn: Callable,
    InputModel: type[BaseModel],
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
                await execute_fn(input_obj, **config.kwargs)
            except Exception:
                logger.exception("execute raised an exception, skipping message")
                continue
```

- [ ] **Step 3: Commit**

```bash
git add fred_ops/runtime/sub.py
git commit -m "refactor(runtime): use connect_broker helper in sub mode"
```

---

## Task 5: Verify implementation and test logs

**Files:**
- Test: `fred_ops/runtime/broker.py`
- Test: `fred_ops/runtime/pub.py`
- Test: `fred_ops/runtime/sub.py`
- Test: `fred_ops/runtime/pubsub.py`

- [ ] **Step 1: Run all unit tests**

Run: `cd /Users/azrrael/Eafit/ops-beacon-services/fred-ops && python -m pytest tests/runtime/test_broker.py -v`

Expected: All tests PASS

- [ ] **Step 2: Verify no syntax errors in runtime files**

Run: `cd /Users/azrrael/Eafit/ops-beacon-services/fred-ops && python -m py_compile fred_ops/runtime/broker.py fred_ops/runtime/pub.py fred_ops/runtime/sub.py fred_ops/runtime/pubsub.py`

Expected: No compilation errors

- [ ] **Step 3: Check imports are correct**

Run: `cd /Users/azrrael/Eafit/ops-beacon-services/fred-ops && python -c "from fred_ops.runtime.broker import connect_broker; from fred_ops.runtime.pub import run_pub; from fred_ops.runtime.sub import run_sub; from fred_ops.runtime.pubsub import run_pubsub; print('✓ All imports successful')"`

Expected: Output `✓ All imports successful`

- [ ] **Step 4: Commit verification**

```bash
git log --oneline -5
```

Expected: Shows 4 commits related to broker connection logging

---

## Spec Coverage Check

✅ **Requirement 1:** Log broker configuration before connecting
- Implemented in `broker.py`: Initial `logger.info()` call with host, port, client_id, auth status

✅ **Requirement 2:** Log success when MQTT connection established
- Implemented in `broker.py`: Success log with connection duration

✅ **Requirement 3:** Log failures with detailed error context
- Implemented in `broker.py`: Error log with host, port, error type, and error message

✅ **Requirement 4:** Fail fast (no retries)
- Implemented in `broker.py`: Exceptions are re-raised immediately, no retry logic

✅ **Requirement 5:** Log all details (host, port, client_id, protocol, timing, auth)
- Implemented in `broker.py`: All details included in logs without exposing passwords

✅ **Code duplication elimination**
- Implemented: `pub.py`, `sub.py`, `pubsub.py` all use centralized `connect_broker()` helper

✅ **Backwards compatibility**
- Implemented: CLI behavior unchanged, existing error handling in `cli.py` still works
