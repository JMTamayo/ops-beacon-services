# Fred-ops: Architecture and Concepts

This document explains how fred-ops works internally, for developers who want to understand or contribute to the framework.

## Table of Contents

1. [Overview](#overview)
2. [Execution Flow](#execution-flow)
3. [Main Components](#main-components)
4. [Dynamic Model Generation](#dynamic-model-generation)
5. [Execution Modes](#execution-modes)
6. [Error Handling](#error-handling)
7. [Extending Fred-ops](#extending-fred-ops)

---

## Overview

Fred-ops is a framework that **abstracts MQTT complexity** behind a simple interface:

```
┌──────────────────────────────────────────────────┐
│  YOUR CODE (business logic)                      │
│                                                  │
│  @app.execute                                    │
│  async def execute(input, output, **kwargs):    │
│      # You only write this                       │
│      return output(processed=input.value * 2)   │
└──────────────────────────┬───────────────────────┘
                           │
                           ▼
            ╔══════════════════════════════╗
            ║      FRED-OPS FRAMEWORK      ║
            ║                              ║
            ║ - MQTT connection mgmt       ║
            ║ - JSON serialization         ║
            ║ - Pydantic validation        ║
            ║ - Async message loop         ║
            ║ - Error handling             ║
            ╚══════════════════════════════╝
                           │
                           ▼
                    ┌─────────────┐
                    │  MQTT Broker│
                    │             │
                    │  Topics &   │
                    │  Messages   │
                    └─────────────┘
```

**Fundamental principle:** Separate **business logic** (what you write) from **infrastructure** (what fred-ops manages).

---

## Execution Flow

When you run `fred-ops run --config config.yml --script processor.py`:

### 1. CLI Initialization

```
$ fred-ops run --config config.yml --script processor.py

    ↓
    
┌─────────────────────────────────────────┐
│ cli.py - main() / run()                 │
│ ├─ Parse arguments                      │
│ ├─ Validate files exist                 │
│ └─ Call load_config()                   │
└─────────────────────────────────────────┘
```

### 2. Configuration Loading

```
load_config(config_path, cli_kwargs)

    ↓
    
┌─────────────────────────────────────────┐
│ config.py - load_config()               │
│ ├─ Read YAML with PyYAML                │
│ ├─ Validate with Pydantic               │
│ ├─ Generate InputModel (dynamic)        │
│ ├─ Generate OutputModel (dynamic)       │
│ └─ Return (config, InputModel,          │
│            OutputModel)                 │
└─────────────────────────────────────────┘

Result:
    config: FredOpsConfig object
    InputModel: Pydantic model class (auto-generated)
    OutputModel: Pydantic model class (auto-generated)
```

### 3. Script Discovery

```
_discover_fred_ops_instance(script_path)

    ↓
    
┌─────────────────────────────────────────┐
│ cli.py - _discover_fred_ops_instance()  │
│ ├─ Import module dynamically            │
│ ├─ Iterate over vars(module)            │
│ ├─ Find FredOps instance                │
│ └─ Get @app.execute function            │
└─────────────────────────────────────────┘

Result:
    app: FredOps instance
    execute_fn: Function decorated with @app.execute
```

### 4. Runner Selection and Execution

```
if config.mode == "pubsub":
    asyncio.run(run_pubsub(config, execute_fn, InputModel, OutputModel))
elif config.mode == "pub":
    asyncio.run(run_pub(config, execute_fn, OutputModel))
elif config.mode == "sub":
    asyncio.run(run_sub(config, execute_fn, InputModel))

    ↓
    
┌─────────────────────────────────────────┐
│ runtime/pubsub.py (or pub.py / sub.py) │
│ ├─ Connect to broker (aiomqtt)          │
│ ├─ Subscribe to topic(s)                │
│ ├─ Enter message loop                   │
│ ├─ Parse JSON → Model                   │
│ ├─ Call execute()                       │
│ ├─ Serialize → JSON                     │
│ ├─ Publish result                       │
│ └─ Error handling                       │
└─────────────────────────────────────────┘
```

---

## Main Components

### 1. FredOps App (`app.py`)

The `FredOps` class is a simple registry:

```python
class FredOps:
    def __init__(self):
        self._execute_fn: Callable | None = None
    
    def execute(self, fn: Callable) -> Callable:
        """Decorator to register the execute function."""
        if self._execute_fn is not None:
            raise RuntimeError("Only one @app.execute allowed")
        self._execute_fn = fn
        return fn
    
    def get_execute(self) -> Callable:
        """Retrieve the registered function."""
        if self._execute_fn is None:
            raise RuntimeError("No execute function registered")
        return self._execute_fn
```

**Why a decorator?**
- Separates function declaration from discovery
- Allows the CLI to search for any `FredOps` instance in the module
- Flexible: you can have multiple services in a monorepo

**Optional `@app.storage`:** Second decorator, at most one function. Invoked after a successful `execute` (signatures differ by mode; see README). `get_storage()` returns `None` if not registered.

**Optional dashboard:** `FredOpsConfig.dashboard` is `None` when the YAML omits `dashboard` or sets `dashboard: null`. When `dashboard.enabled` is true, `cli.py` initializes the SQLite sink (`dashboard/sink.py`), records rows from runtimes (`dashboard/recorder.py`), and spawns `streamlit run` on `dashboard/app.py`. The MQTT process and Streamlit are **separate processes**; data is shared via SQLite (WAL).

### 2. Config Loader (`config.py`)

Converts YAML into typed Python structures:

```python
def load_config(config_path: str, cli_kwargs: dict = None):
    """
    Load and validate config YAML.
    Generate Pydantic models dynamically.
    """
    # 1. Read YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    # 2. Validate base structure
    fred_config = FredOpsConfig(**data)
    
    # 3. Generate dynamic models
    InputModel = None
    OutputModel = None
    
    if fred_config.input:
        InputModel = _create_model_from_schema(
            "InputModel",
            fred_config.input.schema
        )
    
    if fred_config.output:
        OutputModel = _create_model_from_schema(
            "OutputModel",
            fred_config.output.schema
        )
    
    # 4. Merge kwargs (YAML + CLI)
    if cli_kwargs:
        fred_config.kwargs.update(cli_kwargs)  # CLI wins
    
    return fred_config, InputModel, OutputModel
```

**Mode validation:**
- `pubsub`: requires input AND output
- `pub`: requires only output
- `sub`: requires only input

**Exception handling:**
```python
try:
    config, InputModel, OutputModel = load_config(...)
except ConfigError as e:
    # Known errors (missing field, invalid mode)
    raise click.ClickException(str(e))
except Exception as e:
    # Unexpected errors
    raise click.ClickException(f"Config error: {e}")
```

### 3. Model Generation (`config.py`)

Fred-ops uses `pydantic.create_model()` to generate schemas at runtime:

```python
def _create_model_from_schema(name: str, schema: dict) -> type[BaseModel]:
    """
    Convert YAML schema to Pydantic model.
    
    Input:
        schema = {
            "device_id": "str",
            "temperature": "float",
            "active": "bool"
        }
    
    Output:
        InputModel = Pydantic model with three typed fields
    """
    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }
    
    fields = {}
    for field_name, type_str in schema.items():
        if type_str not in type_map:
            raise ConfigError(f"Unknown type: {type_str}")
        
        python_type = type_map[type_str]
        fields[field_name] = (python_type, ...)  # ... = required
    
    return create_model(name, **fields)
```

**Advantages:**
- Schemas defined in YAML, not Python
- Automatic validation with Pydantic
- Automatic JSON serialization/deserialization
- Type hints at runtime

### 4. CLI Discovery (`cli.py`)

The CLI automatically discovers the `FredOps` instance:

```python
def _discover_fred_ops_instance(script_path: str) -> FredOps:
    """
    Dynamically import a Python script.
    Search for the first FredOps instance.
    Return the instance and its @app.execute function.
    """
    # Create a unique module name
    module_key = f"_fred_ops_user_script_{path.stem}_{id(path)}"
    
    # Load the script as a module
    spec = importlib.util.spec_from_file_location(module_key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = module
    spec.loader.exec_module(module)
    
    # Search for FredOps instance
    for obj in vars(module).values():
        if isinstance(obj, FredOps):
            return obj
    
    # Not found
    raise RuntimeError(f"No FredOps instance in '{script_path}'")
```

**Why `importlib`?**
- Does not depend on PYTHONPATH
- The script can be anywhere
- Can be loaded multiple times with unique modules

---

## Dynamic Model Generation

Fred-ops automatically generates Pydantic models from YAML. This is key for type safety at runtime.

### Example

**YAML:**
```yaml
input:
  schema:
    device_id: str
    temperature: float
    readings: list
```

**Generated model:**
```python
class InputModel(BaseModel):
    device_id: str
    temperature: float
    readings: list
```

**Used at runtime:**
```python
# Parsing JSON
data = {"device_id": "s1", "temperature": 25.5, "readings": [1,2,3]}
input_obj = InputModel(**data)

# Automatic validation
input_obj.temperature  # 25.5 (float)
input_obj.device_id    # "s1" (str)

# Serialization
json_str = input_obj.model_dump_json()
```

### Advantages

- **Type safety:** IDE autocompletion, type checkers (mypy)
- **Validation:** Pydantic rejects invalid data
- **Serialization:** `model_dump()`, `model_dump_json()`
- **Documentation:** Fields are available at runtime

---

## Execution Modes

### PUBSUB Mode

**Flow:**
1. Connect to MQTT broker
2. Subscribe to input topic
3. Enter message loop
4. For each message:
   - Parse JSON → InputModel
   - Call `execute(input, OutputModel, **kwargs)`
   - Get result (OutputModel)
   - Serialize → JSON
   - Publish to output topic

**Implementation (pseudocode):**

```python
async def run_pubsub(config, execute_fn, InputModel, OutputModel):
    async with aiomqtt.Client(config.broker.host, ...) as client:
        await client.subscribe(config.input.topic)
        
        async for message in client.messages:
            try:
                # Parse
                payload = json.loads(message.payload)
                input_obj = InputModel(**payload)
                
                # Execute
                result = await execute_fn(
                    input_obj,
                    OutputModel,
                    **config.kwargs
                )
                
                # Publish
                output_json = result.model_dump_json()
                await client.publish(
                    config.output.topic,
                    output_json
                )
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
            except Exception as e:
                logger.error(f"Execute error: {e}")
```

### PUB Mode

**Flow:**
1. Connect to MQTT broker
2. Infinite loop:
   - Call `execute(OutputModel, **kwargs)`
   - Serialize result → JSON
   - Publish to output topic

**Use case:** Generate data periodically (heartbeat, metrics, etc.)

### SUB Mode

**Flow:**
1. Connect to MQTT broker
2. Subscribe to input topic
3. For each message:
   - Parse JSON → InputModel
   - Call `execute(input, **kwargs)` (without OutputModel)
   - No publish (it's a consumer/sink)

**Use case:** Process/store/alert without MQTT output

---

## Error Handling

Fred-ops distinguishes between **recoverable** and **non-recoverable** errors:

### Non-Recoverable Errors

Raised at startup:

```
┌─ Config file not found
├─ YAML parse error (invalid syntax)
├─ Missing required field
├─ Invalid mode
├─ Script not found
├─ No FredOps instance in script
└─ MQTT broker unreachable (initially)
```

**Response:** CLI exits with non-zero code

```python
try:
    fred_config, InputModel, OutputModel = load_config(config_path)
except ConfigError as e:
    raise click.ClickException(str(e))  # Print error, exit(1)
```

### Recoverable Errors

Occur during message processing:

```
┌─ Malformed JSON
├─ Pydantic validation error
├─ execute() throws exception
└─ MQTT connection interrupted (retries)
```

**Response:** Log the error, skip the message, continue

```python
async for message in client.messages:
    try:
        input_obj = InputModel(**json.loads(message.payload))
        result = await execute_fn(input_obj, OutputModel, **kwargs)
        await client.publish(output_topic, result.model_dump_json())
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Message parse failed: {e}")
        # Continue to next message
    
    except Exception as e:
        logger.error(f"Execute failed: {e}", exc_info=True)
        # Continue to next message
```

### Logging

Fred-ops uses the standard Python `logging` module:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Connected to MQTT")
logger.debug(f"Received: {input_obj}")
logger.error(f"Error: {e}", exc_info=True)
```

**Typical output:**
```
2026-04-10 10:23:45.123 - fred_ops.runtime.pubsub - INFO - Connected to MQTT
2026-04-10 10:23:46.456 - fred_ops.runtime.pubsub - DEBUG - Received: InputModel(...)
2026-04-10 10:23:47.789 - fred_ops.runtime.pubsub - INFO - Published to sensors/processed
```

---

## Extending Fred-ops

### Case 1: Add a new schema type

To support more complex types (e.g., `datetime`):

```python
# In config.py
TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "datetime": datetime,  # New
}

def _create_model_from_schema(name: str, schema: dict):
    # ... same code
    # TYPE_MAP now includes datetime
```

### Case 2: Add a new mode

To support a new pattern (e.g., `request-reply`):

```python
# Create runtime/request_reply.py
async def run_request_reply(config, execute_fn, InputModel, OutputModel):
    async with aiomqtt.Client(...) as client:
        await client.subscribe(config.input.topic + "/+/request")
        async for message in client.messages:
            client_id = message.topic.split("/")[1]
            input_obj = InputModel(**json.loads(message.payload))
            result = await execute_fn(input_obj, OutputModel, **kwargs)
            await client.publish(
                f"{config.output.topic}/{client_id}/response",
                result.model_dump_json()
            )

# In cli.py
elif mode == "request_reply":
    asyncio.run(run_request_reply(...))
```

### Case 3: Add custom validation

For more complex validation logic:

```python
@app.execute
async def execute(input, output, **kwargs):
    # Custom validation
    if input.temperature < -50 or input.temperature > 150:
        raise ValueError("Temperature out of range")
    
    # ... normal logic
    return output(...)
```

---

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                    CLI Layer                        │
│  (cli.py)                                           │
│  ├─ Parse arguments                                │
│  ├─ Load config                                    │
│  ├─ Discover FredOps instance                      │
│  └─ Select runner                                  │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│PUBSUB   │ │PUB      │ │SUB      │
│Runner   │ │Runner   │ │Runner   │
│         │ │         │ │         │
│LOOP:   │ │LOOP:   │ │LOOP:   │
│SUB→EXE │ │EXE→PUB │ │SUB→EXE │
│→PUB    │ │        │ │        │
└────┬────┘ └────┬────┘ └────┬────┘
     │            │           │
     └────────────┼───────────┘
                  │
     ┌────────────▼────────────┐
     │  aiomqtt Client         │
     │  (MQTT communication)   │
     │  - connect()            │
     │  - subscribe()          │
     │  - publish()            │
     └────────────┬────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │  MQTT Broker    │
        │  - Topics       │
        │  - Messages     │
        │  - Subscriptions│
        └─────────────────┘
```

---

## Design Decisions

### Why aiomqtt?

- **Async-native:** Allows millions of connections
- **Modern:** Actively maintained, alternative to paho-mqtt
- **Context manager:** Automatically cleans up connections

### Why Pydantic?

- **Validation:** Rejects invalid data
- **Serialization:** Automatic JSON
- **Documentation:** Type hints at runtime

### Why Click for CLI?

- **User-friendly:** Clear error messages
- **Robust:** Argument handling
- **Flexible:** Decorators for subcommands

### Why YAML for config?

- **Readable:** Human-friendly
- **Typed:** Pydantic schemas
- **Standard:** Used in K8s, Docker Compose, etc.

---

## Testing

### Mocking aiomqtt

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_pubsub_publishes_correctly():
    mock_client = MagicMock()
    mock_client.subscribe = AsyncMock()
    mock_client.publish = AsyncMock()
    mock_client.messages = [
        MagicMock(payload='{"value": 10}', topic="input"),
        # ...
    ]
    
    async def execute(input, output, **kwargs):
        return output(doubled=input.value * 2)
    
    with patch("fred_ops.runtime.pubsub.aiomqtt.Client") as mock_mqtt:
        mock_mqtt.return_value.__aenter__.return_value = mock_client
        # ... run test
        
        mock_client.publish.assert_called_with(
            "output/topic",
            '{"doubled": 20}'
        )
```

---

This is the technical heart of fred-ops. Understanding this architecture allows you to:

1. **Contribute:** Add features or modes
2. **Debug:** Understand what fails and where
3. **Optimize:** Identify bottlenecks
4. **Extend:** Customizations for your needs
