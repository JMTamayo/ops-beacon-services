# fred-ops

A Python framework for building MQTT processors with a simple CLI. Write only the business logic — fred-ops handles connection, serialization, and message routing.

## Installation

```bash
# From the monorepo root
uv pip install -e ./fred-ops

# Or directly
cd fred-ops && uv sync
```

## Quick Start

**1. Write a config YAML:**

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

**2. Write your processor:**

```python
# processor.py
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

**3. Run it:**

```bash
fred-ops run --config config.yml --script processor.py
```

## Modes

| Mode | Input | Output | execute signature |
|------|-------|--------|-------------------|
| `pubsub` | ✅ | ✅ | `async def execute(input, output, **kwargs) -> OutputModel` |
| `pub` | ❌ | ✅ | `async def execute(output, **kwargs) -> OutputModel` |
| `sub` | ✅ | ❌ | `async def execute(input, **kwargs) -> None` |

## Config Reference

```yaml
broker:
  host: string          # required
  port: int             # default: 1883
  username: string      # optional
  password: string      # optional
  client_id: string     # optional

mode: pubsub | pub | sub  # required

input:                  # required for pubsub, sub
  topic: string
  schema:
    field_name: str | int | float | bool | list | dict

output:                 # required for pubsub, pub
  topic: string
  schema:
    field_name: str | int | float | bool | list | dict

kwargs:                 # optional, forwarded to execute()
  key: value
```

## CLI Options

```
fred-ops run [OPTIONS]

Options:
  -c, --config TEXT   Path to YAML config file  [required]
  -s, --script TEXT   Path to Python script with FredOps instance  [required]
  -k, --kwarg TEXT    Extra key=value forwarded to execute (repeatable)
```

CLI `--kwarg` values override same-named keys from the YAML `kwargs` section.

## Development

```bash
cd fred-ops
uv sync --dev
uv run pytest tests/ -v
```
