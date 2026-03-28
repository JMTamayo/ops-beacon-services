# fred-ops Framework Design

**Date:** 2026-03-28
**Status:** Approved

## Context

The ops-beacon-services monorepo has several services that consume and produce MQTT messages. Currently, each service reimplements MQTT boilerplate (connection, subscribe, message parsing, error handling). `fred-ops` is a Python framework and CLI that abstracts this boilerplate so developers only write the business logic `execute` function. It lives inside the monorepo as a reusable local package.

## Goal

A pip-installable Python framework that provides:
- A CLI (`fred-ops run`) to launch MQTT processors from a YAML config
- Three execution modes: PUBSUB, PUB, SUB
- Auto-generated Pydantic input/output models from YAML schema definitions
- Async-first execution via aiomqtt

## Architecture

```
┌─────────────────────────────────────────┐
│  CLI (Click)                            │  fred-ops run --config config.yml --script processor.py
├─────────────────────────────────────────┤
│  FredOps (app object)                   │  @app.execute decorator
├─────────────────────────────────────────┤
│  Runtime (pubsub / pub / sub runners)   │  asyncio + aiomqtt
├─────────────────────────────────────────┤
│  Config Loader                          │  YAML → validated FredOpsConfig → dynamic Pydantic models
├─────────────────────────────────────────┤
│  MQTT Client (aiomqtt)                  │  async context manager, connect/subscribe/publish
└─────────────────────────────────────────┘
```

## Project Structure

```
ops-beacon-services/
└── fred-ops/
    ├── pyproject.toml
    ├── README.md
    ├── fred_ops/
    │   ├── __init__.py          # exposes FredOps
    │   ├── app.py               # FredOps class + @execute decorator
    │   ├── cli.py               # Click CLI entry point
    │   ├── config.py            # YAML loader + dynamic Pydantic model generation
    │   └── runtime/
    │       ├── __init__.py
    │       ├── pubsub.py        # PUBSUB runner
    │       ├── pub.py           # PUB runner
    │       └── sub.py           # SUB runner
    ├── tests/
    │   ├── __init__.py
    │   ├── test_config.py       # YAML loading, validation, model generation
    │   ├── test_app.py          # @execute decorator
    │   └── test_runtime/
    │       ├── __init__.py
    │       ├── test_pubsub.py   # PUBSUB runner (mocked aiomqtt)
    │       ├── test_pub.py      # PUB runner
    │       └── test_sub.py      # SUB runner
    └── examples/
        ├── config_pubsub.yml
        ├── config_pub.yml
        ├── config_sub.yml
        └── processor.py
```

## Configuration YAML

```yaml
broker:
  host: localhost
  port: 1883
  username: user        # optional
  password: secret      # optional
  client_id: my-client  # optional

mode: pubsub  # pubsub | pub | sub

input:                  # required for modes: pubsub, sub
  topic: sensors/raw
  schema:
    device_id: str
    temperature: float
    active: bool

output:                 # required for modes: pubsub, pub
  topic: sensors/processed
  schema:
    device_id: str
    alert: bool
    value: float

kwargs:                 # optional — forwarded as **kwargs to execute()
  threshold: 42.5
  region: us-east
  debug: true
```

**Supported schema types:** `str`, `int`, `float`, `bool`, `list`, `dict`

**kwargs behavior:** Values defined under `kwargs` in the YAML are merged with any `--kwarg` flags passed via CLI. CLI flags take precedence over YAML values for the same key.

**Validation rules:**
- `pubsub` requires both `input` and `output`
- `pub` requires only `output`
- `sub` requires only `input`
- Missing required sections raise a clear `ConfigError` at startup

## Config Loader (`config.py`)

1. Reads YAML with PyYAML
2. Validates structure with static Pydantic model `FredOpsConfig`
3. Generates dynamic models with `pydantic.create_model()`:
   - Maps YAML type strings (`"str"`, `"int"`, etc.) to Python types
   - Returns `(InputModel, OutputModel)` tuple (either may be `None` depending on mode)
4. Exposes `config.kwargs: dict` — values from `kwargs` section, merged with CLI `--kwarg` flags (CLI wins on conflict)

## FredOps App Object (`app.py`)

```python
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    return output(value=input.value * 2)
```

`FredOps` stores the decorated function. The CLI imports the script, discovers the `FredOps` instance, retrieves the registered function, and passes it to the appropriate runner.

## Runtime Modes

### PUBSUB

```python
async with aiomqtt.Client(host, port, ...) as client:
    await client.subscribe(input_topic)
    async for message in client.messages:
        input_obj = InputModel(**json.loads(message.payload))
        result = await execute(input_obj, OutputModel, **kwargs)
        await client.publish(output_topic, result.model_dump_json())
```

**execute signature:** `async def execute(input: InputModel, output: type[OutputModel], **kwargs) -> OutputModel`

### PUB

```python
async with aiomqtt.Client(host, port, ...) as client:
    while True:
        result = await execute(OutputModel, **kwargs)
        await client.publish(output_topic, result.model_dump_json())
```

**execute signature:** `async def execute(output: type[OutputModel], **kwargs) -> OutputModel`

Runs indefinitely until SIGINT/SIGTERM.

### SUB

```python
async with aiomqtt.Client(host, port, ...) as client:
    await client.subscribe(input_topic)
    async for message in client.messages:
        input_obj = InputModel(**json.loads(message.payload))
        await execute(input_obj, **kwargs)
```

**execute signature:** `async def execute(input: InputModel, **kwargs) -> None`

## CLI (`cli.py`)

```
fred-ops run --config config.yml --script processor.py [--kwarg key=value ...]
```

Options:
- `--config` / `-c`: path to YAML config (required)
- `--script` / `-s`: path to user Python script containing FredOps instance (required)
- `--kwarg` / `-k`: extra key=value pairs forwarded as `**kwargs` to execute (optional, repeatable)

The CLI:
1. Loads and validates config from YAML
2. Imports the user script as a module
3. Finds the `FredOps` instance in the module's globals
4. Selects the runner based on `config.mode`
5. Calls `asyncio.run(runner(config, execute_fn, input_model, output_model, kwargs))`

## Packaging (`pyproject.toml`)

```toml
[project]
name = "fred-ops"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "aiomqtt>=2.0.0",
    "click>=8.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
]

[project.scripts]
fred-ops = "fred_ops.cli:main"

[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24"]
```

Local install:
```bash
# from monorepo root
uv pip install -e ./fred-ops

# or from fred-ops directory
cd fred-ops && uv sync
```

## Testing

- **`test_config.py`**: valid YAML loads correctly, invalid mode raises `ConfigError`, missing input/output for mode raises error, schema types map to correct Python types
- **`test_app.py`**: `@app.execute` stores the function, calling `app.get_execute()` returns it
- **`test_runtime/test_pubsub.py`**: mocked aiomqtt client, verifies execute called with correct `InputModel` instance and `OutputModel` class, verifies publish called with serialized result
- **`test_runtime/test_pub.py`**: verifies execute called with `OutputModel` class, verifies publish called in loop
- **`test_runtime/test_sub.py`**: verifies execute called with `InputModel` instance, verifies no publish call

All async tests use `pytest-asyncio` with `asyncio_mode = "auto"`.

## Error Handling

- **Config errors**: raised at startup before connecting (invalid YAML, missing fields, type mismatch)
- **Message parse errors**: logged and skipped (malformed JSON or Pydantic validation error on incoming message)
- **MQTT connection errors**: aiomqtt raises exceptions; runners propagate to CLI which exits with non-zero code
- **execute exceptions**: logged with traceback, message skipped (for SUB/PUBSUB); loop continues

## Verification

```bash
# Install
cd ops-beacon-services/fred-ops
uv sync

# Run tests
uv run pytest tests/ -v

# Run example (requires MQTT broker at localhost:1883)
uv run fred-ops run --config examples/config_pubsub.yml --script examples/processor.py
```
