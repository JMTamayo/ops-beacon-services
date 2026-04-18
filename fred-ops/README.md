# fred-ops Framework

A Python framework for building MQTT processors with zero boilerplate. Write only the **business logic** — fred-ops handles MQTT connection, serialization, message routing, and async lifecycle management.

**Key insight:** fred-ops eliminates the need to reimplement MQTT plumbing in every service. Define your input/output schemas in YAML, write an async function, and deploy.

---

## 📋 Table of Contents

- [What is fred-ops?](#what-is-fred-ops)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Modes: PUB, SUB, PUBSUB](#modes)
- [Creating a New Service](#creating-a-new-service)
- [Configuration Reference](#configuration-reference)
- [Examples](#examples)
- [Architecture](#architecture)
- [Development & Testing](#development--testing)

---

## What is fred-ops?

Fred-ops is a **framework and CLI** that abstracts MQTT boilerplate so you can focus on business logic. Instead of:

1. Managing MQTT connections and subscriptions
2. Parsing and validating messages
3. Serializing and publishing results
4. Handling reconnection and error cases

You write:

```python
@app.execute
async def execute(input, output, **kwargs):
    # your business logic here
    return output(processed_value=input.raw_value * 2)
```

Everything else is handled by fred-ops.

### Why fred-ops?

- **Zero boilerplate:** No connection management code, no JSON parsing, no reconnection logic
- **Three execution modes:** Process messages (PUBSUB), produce messages (PUB), consume messages (SUB)
- **Type-safe:** Auto-generated Pydantic models from YAML schemas
- **Async-first:** Built on `aiomqtt` for high-concurrency message processing
- **Optional persistence hook:** `@app.storage` runs after a successful `execute` (per mode) for DB or audit trails
- **Optional Streamlit dashboard:** Time series and tables from processed events (SQLite + separate process)
- **Monorepo-friendly:** Installed as a local package in ops-beacon-services

---

## Installation

### From the monorepo root:

```bash
uv pip install -e ./fred-ops
```

### Or, in the fred-ops directory:

```bash
cd fred-ops
uv sync
```

This installs fred-ops globally in your environment and makes the `fred-ops` CLI available.

### Optional: Streamlit dashboard

For a live time-series view of processed MQTT payloads (SQLite-backed), install the extra and add a `dashboard` section to YAML:

```bash
uv pip install -e ".[dashboard]"
```

- **Omit the `dashboard` key** (or set `dashboard: null`) to disable the UI and avoid starting Streamlit.
- With a `dashboard` section, **every field is optional**; defaults apply when omitted (`enabled` defaults to `false` until you set it to `true`).

```yaml
dashboard:
  enabled: true
  # port: 8501
  # host: "0.0.0.0"
  # max_rows: 2000
```

Run `fred-ops run ...` as usual; when `enabled: true`, the dashboard process starts alongside the processor. Open `http://localhost:<port>` (default 8501).

Timestamps are shown as human-readable datetimes (default timezone `America/Bogota`; override with env `FRED_OPS_DASHBOARD_TZ`, e.g. `UTC`). The chart uses **Altair** so date labels stay formatted when you expand or zoom the chart; the table shows **numeric and non-numeric** fields from input/output JSON.

### Optional: `@app.storage` (persist after `execute`)

Register **at most one** optional function to persist or audit data **after** `execute` completes without error:

| Mode | Signature (conceptual) |
|------|-------------------------|
| `sub` | `async def storage(input, **kwargs)` — same validated `input` as `execute` |
| `sub` + `generic_event_log` | `async def storage(mqtt_topic=..., payload_json=..., payload_bytes=..., **kwargs)` |
| `pubsub` | `async def storage(input, result, **kwargs)` — `result` is the output model instance |
| `pub` | `async def storage(result, **kwargs)` |

If you omit `@app.storage`, nothing is registered. Storage errors are logged and do not stop the MQTT loop (in `pubsub`, publish already happened before storage runs).

---

## Quick Start

### 1. Create a config file (`config.yml`):

```yaml
broker:
  host: localhost
  port: 1883

mode: pubsub

input:
  topic: sensors/raw
  schema:
    device_id: str
    temperature: float

output:
  topic: sensors/processed
  schema:
    device_id: str
    alert: bool

kwargs:
  threshold: 30.0
```

### 2. Create a processor script (`processor.py`):

```python
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    threshold = float(kwargs.get("threshold", 25.0))
    return output(
        device_id=input.device_id,
        alert=input.temperature > threshold,
    )
```

### 3. Run it:

```bash
fred-ops run --config config.yml --script processor.py
```

That's it. Your processor is now listening on `sensors/raw` and publishing to `sensors/processed`.

---

## Modes

Fred-ops supports three execution modes determined by your config:

| Mode | Input | Output | Purpose | execute() signature |
|------|-------|--------|---------|----------------------|
| **PUBSUB** | ✅ | ✅ | Subscribe to input topic, transform, publish to output | `async def execute(input, output, **kwargs) -> OutputModel` |
| **PUB** | ❌ | ✅ | Generate and publish messages (producer) | `async def execute(output, **kwargs) -> OutputModel` |
| **SUB** | ✅ | ❌ | Subscribe and consume, no output (sink) | `async def execute(input, **kwargs) -> None` |

### PUBSUB Example

Process incoming messages: read from one topic, transform, write to another.

```yaml
mode: pubsub
input:
  topic: raw/events
  schema:
    event_type: str
    timestamp: int
output:
  topic: processed/events
  schema:
    event_type: str
    severity: str
```

```python
@app.execute
async def execute(input, output, **kwargs):
    severity = "HIGH" if input.event_type == "ERROR" else "LOW"
    return output(event_type=input.event_type, severity=severity)
```

### PUB Example

Generate messages on a schedule or on-demand (e.g., health check, heartbeat).

```yaml
mode: pub
output:
  topic: heartbeat/service
  schema:
    service_name: str
    status: str
    timestamp: int
```

```python
import time
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(output, **kwargs):
    return output(
        service_name="my-service",
        status="healthy",
        timestamp=int(time.time()),
    )
```

The loop runs indefinitely, calling `execute()` repeatedly.

### SUB Example

Consume messages and perform side effects (e.g., log, store, trigger action).

```yaml
mode: sub
input:
  topic: alerts/critical
  schema:
    alert_id: str
    message: str
    severity: str
```

```python
@app.execute
async def execute(input, **kwargs):
    print(f"[{input.severity}] {input.message}")
    # Store to database, send email, etc.
    # No output needed
```

---

## Creating a New Service

Follow these steps to create a new fred-ops service in your project:

### Step 1: Create the service directory

```bash
mkdir -p my-service/{config,src}
cd my-service
```

### Step 2: Create the configuration file (`config/processor.yml`)

Define your input/output topics and schemas:

```yaml
broker:
  host: mqtt.example.com
  port: 1883
  username: user
  password: pass

mode: pubsub  # or pub, sub

input:
  topic: raw/data
  schema:
    id: str
    value: float
    timestamp: int

output:
  topic: processed/data
  schema:
    id: str
    result: float
    processed_at: int

kwargs:
  multiplier: 2.5
  debug: false
```

**Schema types:** `str`, `int`, `float`, `bool`, `list`, `dict`

### Step 3: Create the processor script (`src/processor.py`)

Implement your business logic:

```python
"""
My processor: reads raw data, applies a multiplier, publishes result.
"""
import time
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    multiplier = float(kwargs.get("multiplier", 1.0))
    result = input.value * multiplier
    
    return output(
        id=input.id,
        result=result,
        processed_at=int(time.time()),
    )
```

**Important:**
- The `execute()` function **must be async**
- Parameter names match your config exactly (e.g., `input`, `output`)
- Return an instance of `output()` for PUBSUB/PUB modes
- Return `None` for SUB mode
- Use `**kwargs` to access config values
- Optionally add `@app.storage` for persistence after a successful `execute` (see [Installation](#installation))

### Step 4: Run the service

```bash
fred-ops run --config config/processor.yml --src/processor.py
```

### Step 5 (optional): Override config values from CLI

```bash
fred-ops run \
  --config config/processor.yml \
  --script src/processor.py \
  --kwarg multiplier=5.0 \
  --kwarg debug=true
```

CLI kwargs override YAML values with the same key.

### Step 6 (optional): Add to Docker or systemd

For production, wrap the `fred-ops run` command in a Docker container or systemd service:

**Dockerfile:**
```dockerfile
FROM python:3.13-slim
RUN pip install uv
WORKDIR /app
COPY . .
RUN uv pip install -e ./fred-ops
CMD ["fred-ops", "run", "--config", "config/processor.yml", "--script", "src/processor.py"]
```

**systemd service:**
```ini
[Unit]
Description=My Fred-ops Service
After=network.target

[Service]
Type=simple
User=fred
WorkingDirectory=/opt/my-service
ExecStart=/path/to/venv/bin/fred-ops run --config config/processor.yml --script src/processor.py
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

---

## Configuration Reference

### Full Config Structure

```yaml
# Connection settings
broker:
  host: string              # MQTT broker hostname (required)
  port: int                 # MQTT broker port (default: 1883)
  username: string          # Optional auth username
  password: string          # Optional auth password
  client_id: string         # Optional MQTT client ID (auto-generated if omitted)

# Execution mode (required)
mode: pubsub | pub | sub

# Input topic and schema (required for pubsub, sub)
input:
  topic: string             # MQTT topic to subscribe to
  schema:                   # Field definitions
    field_name: str | int | float | bool | list | dict

# Output topic and schema (required for pubsub, pub)
output:
  topic: string             # MQTT topic to publish to
  schema:                   # Field definitions
    field_name: str | int | float | bool | list | dict

# Optional kwargs passed to execute() (optional)
kwargs:
  key1: value1
  key2: value2

# Optional: Streamlit dashboard (omit key or use null to disable entirely)
# dashboard:
#   enabled: false          # default when section is present but you turn UI off
#   port: 8501
#   host: "0.0.0.0"
#   max_rows: 2000          # SQLite row cap for telemetry
#   sqlite_path: null       # default: .fred-ops-dashboard.db in cwd
```

### Optional: `dashboard`

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | When `true`, starts a Streamlit process and records events to SQLite for the UI |
| `port` | `8501` | HTTP port for Streamlit |
| `host` | `0.0.0.0` | Bind address |
| `max_rows` | `2000` | Max rows stored in SQLite (rolling window) |
| `sqlite_path` | *(cwd)* `.fred-ops-dashboard.db` | SQLite database path |

Omit the entire `dashboard` key (or set `dashboard: null`) if you do not want the dashboard or the telemetry file. If a `dashboard` key exists, every field is optional and defaults apply when omitted.

Requires `pip install 'fred-ops[dashboard]'` (Streamlit, pandas, Altair).

### Mode Validation Rules

| Mode | Requires `input` | Requires `output` | Error if missing |
|------|------------------|-------------------|------------------|
| `pubsub` | ✅ | ✅ | Both required |
| `pub` | ❌ | ✅ | output required |
| `sub` | ✅ | ❌ | input required |

### Schema Type Mapping

Each field in `input.schema` and `output.schema` maps to a Python type:

| YAML Type | Python Type | Example |
|-----------|-------------|---------|
| `str` | `str` | `"hello"` |
| `int` | `int` | `42` |
| `float` | `float` | `3.14` |
| `bool` | `bool` | `true` |
| `list` | `list` | `[1, 2, 3]` |
| `dict` | `dict` | `{"key": "value"}` |

### kwargs Behavior

Values in the `kwargs` section are passed to your `execute()` function:

```yaml
kwargs:
  threshold: 25.5
  region: us-east-1
  debug: true
```

Accessed in code:

```python
@app.execute
async def execute(input, output, **kwargs):
    threshold = float(kwargs.get("threshold", 0.0))
    region = kwargs.get("region", "us-west")
    debug = kwargs.get("debug", False) == "true"
```

**CLI override:** Use `--kwarg` to override:

```bash
fred-ops run --config config.yml --script processor.py --kwarg threshold=30.0
```

---

## Examples

### Example 1: Temperature Alert (PUBSUB)

**File structure:**
```
temp-alert/
├── config/
│   └── processor.yml
└── src/
    └── processor.py
```

**config/processor.yml:**
```yaml
broker:
  host: mqtt.local
  port: 1883

mode: pubsub

input:
  topic: sensors/temperature
  schema:
    sensor_id: str
    celsius: float

output:
  topic: alerts/temperature
  schema:
    sensor_id: str
    alert: bool
    message: str

kwargs:
  high_threshold: 35.0
  low_threshold: 5.0
```

**src/processor.py:**
```python
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    high = float(kwargs.get("high_threshold", 30.0))
    low = float(kwargs.get("low_threshold", 0.0))
    
    if input.celsius > high:
        message = f"Temperature too high: {input.celsius}°C"
        alert = True
    elif input.celsius < low:
        message = f"Temperature too low: {input.celsius}°C"
        alert = True
    else:
        message = f"Temperature normal: {input.celsius}°C"
        alert = False
    
    return output(
        sensor_id=input.sensor_id,
        alert=alert,
        message=message,
    )
```

**Run:**
```bash
fred-ops run --config config/processor.yml --script src/processor.py
```

### Example 2: Heartbeat Service (PUB)

**config/processor.yml:**
```yaml
broker:
  host: mqtt.local
  port: 1883

mode: pub

output:
  topic: service/heartbeat
  schema:
    service_name: str
    status: str
    uptime_seconds: int
```

**src/processor.py:**
```python
import time
from fred_ops import FredOps

app = FredOps()

start_time = time.time()

@app.execute
async def execute(output, **kwargs):
    service_name = kwargs.get("service_name", "unknown-service")
    uptime = int(time.time() - start_time)
    
    return output(
        service_name=service_name,
        status="healthy",
        uptime_seconds=uptime,
    )
```

**Run:**
```bash
fred-ops run --config config/processor.yml --script src/processor.py --kwarg service_name=my-service
```

### Example 3: Event Logger (SUB)

**config/processor.yml:**
```yaml
broker:
  host: mqtt.local
  port: 1883

mode: sub

input:
  topic: system/events
  schema:
    event_id: str
    event_type: str
    details: str
    timestamp: int
```

**src/processor.py:**
```python
from datetime import datetime
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, **kwargs):
    dt = datetime.fromtimestamp(input.timestamp).isoformat()
    print(f"[{dt}] {input.event_type} (ID: {input.event_id})")
    print(f"  Details: {input.details}")
    # In production, write to database or log file
```

**Run:**
```bash
fred-ops run --config config/processor.yml --script src/processor.py
```

---

## Architecture

### How Fred-ops Works

```
┌─────────────────────────────────────────────┐
│  CLI (Click)                                │
│  $ fred-ops run --config X --script Y      │
└────────────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Load & Validate Config    │
        │  (YAML → FredOpsConfig)    │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Generate Pydantic Models  │
        │  (InputModel, OutputModel) │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Import User Script        │
        │  Discover FredOps instance │
        │  Get execute() / storage() │
        │  Init dashboard (if any)   │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Select Runner (PUBSUB/   │
        │  PUB/SUB)                  │
        └────────────┬───────────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
       ┌────┐   ┌────┐    ┌────┐
       │PUB │   │SUB │    │PUB │
       │SUB │   │    │    │    │
       └─┬──┘   └─┬──┘    └─┬──┘
         │        │         │
         └────────┼─────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │  aiomqtt Client (async)     │
    │  - Connect to broker        │
    │  - Subscribe/Publish        │
    │  - Message loop             │
    └─────────────────────────────┘
```

### File Organization

```
fred-ops/
├── fred_ops/
│   ├── __init__.py          # Exports FredOps
│   ├── app.py               # FredOps: @execute, optional @storage
│   ├── cli.py               # Click CLI, script discovery, optional Streamlit child
│   ├── config.py            # YAML loader, Pydantic models (incl. optional dashboard)
│   ├── dashboard/           # Streamlit app, SQLite sink, telemetry recorder
│   └── runtime/
│       ├── __init__.py
│       ├── broker.py        # MQTT client (aiomqtt)
│       ├── pubsub.py        # PUBSUB runner
│       ├── pub.py           # PUB runner
│       └── sub.py           # SUB runner (incl. generic_event_log)
├── tests/
│   ├── test_config.py       # YAML parsing, validation, model generation
│   ├── test_app.py          # FredOps decorator and registration
│   └── test_runtime/
│       ├── test_pubsub.py   # PUBSUB runner with mocked aiomqtt
│       ├── test_pub.py      # PUB runner
│       └── test_sub.py      # SUB runner
├── examples/
│   ├── config_pubsub.yml
│   ├── config_pub.yml
│   ├── config_sub.yml
│   └── processor.py
├── pyproject.toml           # Dependencies and metadata
└── README.md                # This file
```

### Runtime Flow

#### PUBSUB Mode

1. Connect to MQTT broker
2. Subscribe to input topic
3. For each message:
   - Parse JSON → InputModel instance
   - Call `execute(input, OutputModel, **kwargs)`
   - Serialize result → JSON
   - Publish to output topic
   - Optional: `storage(input, result, **kwargs)`; optional dashboard row
   - If `storage` raises: logged only (publish already sent)

#### PUB Mode

1. Connect to MQTT broker
2. Infinite loop:
   - Call `execute(OutputModel, **kwargs)`
   - Serialize result → JSON
   - Publish to output topic
   - Optional: `storage(result, **kwargs)`; optional dashboard row

#### SUB Mode

1. Connect to MQTT broker
2. Subscribe to input topic
3. For each message:
   - Parse JSON → InputModel instance (or generic_event_log path)
   - Call `execute(...)`
   - Optional: `storage(...)` with the same shape as execute; optional dashboard row
   - (No publish)

### Error Handling

| Error Type | Behavior |
|-----------|----------|
| **Config error** (missing field, invalid YAML) | Raised at startup, CLI exits with message |
| **Message parse error** (malformed JSON, validation fails) | Logged, message skipped, loop continues |
| **MQTT connection error** | Raised, CLI exits |
| **execute() exception** | Logged with traceback, message/iteration skipped, loop continues |

---

## Development & Testing

### Setup

```bash
cd fred-ops
uv sync --dev
```

### Run Tests

```bash
uv run pytest tests/ -v
```

All async tests use `pytest-asyncio` with automatic mode detection.

### Test Coverage

- **test_config.py:** YAML loading, validation, schema type mapping
- **test_app.py:** FredOps instance, @execute decorator, registration
- **test_runtime/:**
  - `test_pubsub.py`: Message subscribe, execute, publish (mocked aiomqtt)
  - `test_pub.py`: Execute loop, publish
  - `test_sub.py`: Subscribe, execute (no publish)

### Example: Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Specific test file
uv run pytest tests/test_app.py -v

# Specific test
uv run pytest tests/test_app.py::test_execute_decorator -v
```

### Adding a New Feature

1. Write a test in `tests/`
2. Run tests (they fail)
3. Implement the feature
4. All tests pass
5. Commit

Example: Add timeout support to config

```python
# tests/test_config.py
def test_config_with_timeout():
    config_dict = {..., "timeout": 30}
    cfg, _, _ = load_config(config_dict)
    assert cfg.timeout == 30
```

---

## CLI Reference

```
fred-ops run [OPTIONS]

Options:
  -c, --config TEXT   Path to YAML config file (required)
  -s, --script TEXT   Path to Python script with FredOps instance (required)
  -k, --kwarg TEXT    Extra key=value forwarded to execute (repeatable)

Examples:
  fred-ops run --config config.yml --script processor.py
  fred-ops run -c config.yml -s processor.py -k threshold=30 -k debug=true
```

### Kwarg Precedence

1. CLI `--kwarg` flags (highest priority)
2. YAML `kwargs` section
3. Function defaults in `execute()`

```bash
# YAML has threshold: 25, CLI overrides to 30
fred-ops run --config config.yml --script processor.py --kwarg threshold=30
```

---

## Troubleshooting

### No FredOps instance found in script

**Error:** `No FredOps instance found in 'processor.py'`

**Fix:** Ensure your script has:

```python
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(...):
    ...
```

### Cannot connect to broker

**Error:** `Connection refused` or `Unknown host`

**Fix:**
- Check broker `host` and `port` in config
- Verify broker is running
- Check network/firewall

### Invalid schema type

**Error:** `ConfigError: Unknown type 'datetime'`

**Fix:** Use supported types: `str`, `int`, `float`, `bool`, `list`, `dict`

### Pydantic validation error on incoming message

**Error:** `Validation error: field required`

**Fix:**
- Ensure JSON messages match input schema
- Check field names (case-sensitive)
- Ensure all required fields are present

---

## Contributing

To improve fred-ops:

1. Fork or branch
2. Make changes with tests
3. Run `uv run pytest tests/ -v`
4. Submit PR

---

## License

Part of the ops-beacon-services monorepo.
