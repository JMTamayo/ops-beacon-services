# dth-11-processor Template Design

**Date:** 2026-03-28
**Status:** Approved

## Context

The ops-beacon-services monorepo uses fred-ops to build MQTT processors. A template processor for the DHT11 temperature and humidity sensor is needed to serve as a reference for future sensor integrations.

## Goal

Create a reusable template processor that:
- Receives DHT11 sensor readings via MQTT (temperature, humidity, device ID)
- Logs all incoming messages to console in a readable format
- Demonstrates SUB mode (receive-only) using fred-ops framework

## Architecture

```
dth-11-processor/
├── config.yml           # YAML configuration (broker, MQTT topic, schema)
└── processor.py         # FredOps execute function with logging logic
```

### Components

**config.yml:**
- Broker configuration (host, port, optional credentials)
- Mode: `sub` (receive-only)
- Input topic: `sensor/dth11`
- Input schema: defines temperature (float), humidity (float), device_id (str)
- kwargs: empty (no additional parameters needed)

**processor.py:**
- Imports `FredOps` from fred-ops framework
- Creates `app = FredOps()` instance
- Decorates `async def execute(input, **kwargs)` with `@app.execute`
- Logs each received message to console with timestamp, device_id, temperature, humidity

### Data Flow

```
MQTT Broker (sensor/dth11 topic)
    ↓
fred-ops SUB runner
    ↓
Message parsed to InputModel (temperature, humidity, device_id)
    ↓
execute() function
    ↓
Console log output
```

### Configuration Details

```yaml
broker:
  host: localhost
  port: 1883

mode: sub

input:
  topic: sensor/dth11
  schema:
    device_id: str
    temperature: float
    humidity: float

kwargs: {}
```

### Processor Function Signature

```python
@app.execute
async def execute(input: InputModel, **kwargs) -> None:
    # input.device_id: str
    # input.temperature: float
    # input.humidity: float
    # Log to console
```

No output because SUB mode receives only; execute returns None.

## Logging Format

Console output example:
```
[2026-03-28 14:32:15] Device: sensor-01 | Temp: 25.5°C | Humidity: 60.2%
[2026-03-28 14:32:20] Device: sensor-01 | Temp: 25.6°C | Humidity: 60.1%
```

## Error Handling

- Invalid MQTT connection: fred-ops runner propagates exception, CLI exits
- Malformed message (missing fields, type mismatch): fred-ops logs error and skips message
- execute() exceptions: fred-ops logs traceback, continues listening

## Verification

```bash
# Navigate to processor directory
cd dth-11-processor

# Run processor (requires MQTT broker with sensor publishing to sensor/dth11)
fred-ops run --config config.yml --script processor.py
```

## Scope

This is a minimal, receive-only template. Does not include:
- Message filtering or thresholds
- Data persistence
- PUBSUB transformations
- Custom kwargs

These can be added as extensions.
