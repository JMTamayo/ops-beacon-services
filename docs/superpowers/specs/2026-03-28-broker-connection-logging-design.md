---
title: Broker Connection Logging Design
date: 2026-03-28
status: approved
---

# Broker Connection Logging Design

## Overview
Add comprehensive logging to the FredOps CLI to display broker connection status, configuration details, and errors when the MQTT broker connection is established, fails, or encounters issues. The system should fail fast (no reconnection retries) and log complete connection details including timings, protocol version, and authentication info.

## Requirements

### Functional Requirements
1. Log broker configuration **before** attempting connection (host, port, client_id, protocol version)
2. Log **success** when MQTT connection is established, including connection duration
3. Log **failures** with detailed error context when connection fails
4. Fail fast: if connection fails, exit immediately without retries
5. Log all details: host, port, client_id, protocol version, timing, auth method (without showing passwords)

### Non-Functional Requirements
- No silent failures or reconnection loops
- Clear error messages that help users diagnose issues
- Minimal code duplication (connection logic is currently in 3 files)
- Backwards compatible with existing CLI behavior

## Design

### 1. New Module: `fred_ops/runtime/broker.py`

Create a centralized broker connection helper that:
- Manages MQTT client creation with logging
- Logs configuration details before attempting connection
- Logs success/failure with appropriate detail levels
- Handles connection errors gracefully
- Returns the connected aiomqtt.Client instance

**Function signature:**
```python
async def connect_broker(config: BrokerConfig) -> aiomqtt.Client:
    """
    Connect to MQTT broker with comprehensive logging.

    Logs:
    - INFO (pre-connection): configuration details (host, port, client_id, protocol)
    - INFO (success): connection established with timing
    - ERROR (failure): detailed error context for debugging

    Args:
        config: BrokerConfig with host, port, username, password, client_id

    Returns:
        Connected aiomqtt.Client instance

    Raises:
        Propagates connection exceptions to caller (fail fast)
    """
```

### 2. Logging Details

#### Pre-Connection Log (INFO level)
```
[INFO] Conectando a Broker MQTT: host=localhost, port=1883, client_id=fred-ops-abc123, protocol=v3.1.1, autenticación=activada
```

#### Success Log (INFO level)
```
[INFO] ✓ Conexión al Broker MQTT establecida (duración: 0.24s)
```

#### Failure Logs (ERROR level)
Examples of different failure scenarios:
```
[ERROR] ✗ Error al conectar a Broker MQTT en localhost:1883 — Conexión rechazada. Verifica que el Broker esté activo y accesible.

[ERROR] ✗ Error de autenticación en Broker MQTT localhost:1883 — Revisa usuario/contraseña en la configuración.

[ERROR] ✗ Timeout al conectar a Broker MQTT localhost:1883 — El broker no responde. Verifica conectividad de red y que esté disponible.
```

### 3. Refactoring Existing Files

Update `pub.py`, `sub.py`, and `pubsub.py` to use the new helper:

**Before:**
```python
async with aiomqtt.Client(
    hostname=broker.host,
    port=broker.port,
    username=broker.username,
    password=broker.password,
    identifier=broker.client_id,
    protocol_version=aiomqtt.ProtocolVersion.V311,
) as client:
    # process messages
```

**After:**
```python
client = await connect_broker(config.broker)
async with client:
    # process messages
```

### 4. Error Handling

- Connection exceptions are captured and logged with full context
- Exceptions are re-raised to propagate to CLI (fail fast behavior)
- CLI's existing exception handling in `cli.py` catches and displays to user
- No retry logic; user must fix config and restart

### 5. Implementation Details

- Use `time.perf_counter()` to measure connection duration
- Log authentication status without exposing passwords (e.g., "auth=enabled" not actual password)
- Include all BrokerConfig fields in pre-connection log
- Use Python's standard logging module (already imported in runtime files)
- Maintain protocol version constant (V311) as per existing code

## Integration Points

1. **cli.py** — no changes needed (existing error handling works)
2. **pub.py** — replace aiomqtt.Client creation with `await connect_broker(config.broker)`
3. **sub.py** — replace aiomqtt.Client creation with `await connect_broker(config.broker)`
4. **pubsub.py** — replace aiomqtt.Client creation with `await connect_broker(config.broker)`
5. **config.py** — no changes needed

## Success Criteria

- ✅ All three runtime files use the new broker.py helper
- ✅ Pre-connection log shows full config (host, port, client_id, auth status, protocol)
- ✅ Success log shows connection duration
- ✅ Failure logs include error type and helpful context
- ✅ Existing CLI behavior unchanged
- ✅ No reconnection retries (fail fast)
- ✅ Passwords are never logged

## Out of Scope

- Persistent logging to files (only stdout/stderr)
- Configurable log levels via CLI flags
- Retry/backoff logic
- Connection pooling or keep-alive configuration
