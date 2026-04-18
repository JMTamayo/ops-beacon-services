# Guide: Creating a New Fred-ops Service

This guide will walk you step-by-step through creating a new MQTT service using fred-ops, from conception to execution.

## Table of Contents

1. [Planning](#1-planning)
2. [Directory Structure](#2-directory-structure)
3. [Writing the Configuration](#3-writing-the-configuration)
4. [Implementing the Processor](#4-implementing-the-processor)
5. [Local Testing](#5-local-testing)
6. [Deployment](#6-deployment)

---

## 1. Planning

Before writing code, define:

### Key Questions

- **What is the goal?** Process data? Generate events? Consume and store?
- **Which mode?**
  - **PUBSUB:** Read from a topic, transform, write to another topic
  - **PUB:** Generate messages continuously
  - **SUB:** Read messages and perform actions (no output)
- **What data arrives?** (input schema)
- **What data leaves?** (output schema)
- **Do you need configurable parameters?** (kwargs)

### Planning Example

```
Service: temperature-aggregator
Description: Collects temperature readings from multiple sensors
             and generates statistics every minute

Mode: PUBSUB
Input: 
  - Topic: sensors/temperature
  - Fields: sensor_id (str), celsius (float), timestamp (int)
Output:
  - Topic: metrics/temperature/summary
  - Fields: count (int), avg_temp (float), min_temp (float), 
            max_temp (float), recorded_at (int)
Parameters: none
```

---

## 2. Directory Structure

Create a clear and consistent structure:

```bash
mkdir -p my-service/{config,src,tests}
cd my-service
```

This creates:

```
my-service/
├── config/
│   └── processor.yml           # YAML Configuration
├── src/
│   ├── processor.py            # Main logic
│   └── helpers.py              # Helper functions (optional)
└── tests/
    └── test_processor.py       # Unit tests (optional)
```

---

## 3. Writing the Configuration

### Step 3.1: Create `config/processor.yml`

```yaml
# config/processor.yml
broker:
  host: localhost
  port: 1883

mode: pubsub

input:
  topic: sensors/temperature
  schema:
    sensor_id: str
    celsius: float
    timestamp: int

output:
  topic: metrics/temperature
  schema:
    count: int
    avg_temp: float
    min_temp: float
    max_temp: float
    recorded_at: int

kwargs:
  window_size: 10
  debug: false
```

### Configuration Decision Guide

| Question | Option A | Option B |
|----------|----------|----------|
| Do I need input? | mode: `pubsub` or `sub` | mode: `pub` |
| Do I need output? | mode: `pubsub` or `pub` | mode: `sub` |
| String or number? | `str` | `int` / `float` |
| Collection of data? | `list` or `dict` | Avoid if possible |

---

## 4. Implementing the Processor

### Step 4.1: Create `src/processor.py`

Basic structure:

```python
"""
Temperature Aggregator Service
Processes temperature readings and generates statistics.
"""
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    """
    Process a temperature reading.
    
    Args:
        input: Input model (sensor_id, celsius, timestamp)
        output: Output class to create the result
        **kwargs: Configuration parameters
    
    Returns:
        Output instance with statistics
    """
    # Your logic here
    pass
```

### Step 4.2: Implement the Logic

**Simple case (PUBSUB):**

```python
from fred_ops import FredOps
import time

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    # Get parameters
    debug = kwargs.get("debug", False)
    
    # Business logic
    celsius = input.celsius
    alert = celsius > 35
    
    if debug:
        print(f"Sensor {input.sensor_id}: {celsius}°C")
    
    # Return result
    return output(
        count=1,
        avg_temp=celsius,
        min_temp=celsius,
        max_temp=celsius,
        recorded_at=int(time.time()),
    )
```

**Case with state (aggregate data):**

```python
from fred_ops import FredOps
from collections import deque
import time

app = FredOps()

# Shared state between messages
temperature_buffer = deque(maxlen=10)

@app.execute
async def execute(input, output, **kwargs):
    window_size = int(kwargs.get("window_size", 10))
    
    # Update buffer
    temperature_buffer.append(input.celsius)
    
    # Calculate statistics
    temps = list(temperature_buffer)
    
    return output(
        count=len(temps),
        avg_temp=sum(temps) / len(temps),
        min_temp=min(temps),
        max_temp=max(temps),
        recorded_at=int(time.time()),
    )
```

**PUB case (generate data):**

```python
import time
from fred_ops import FredOps

app = FredOps()
start_time = time.time()

@app.execute
async def execute(output, **kwargs):
    uptime = int(time.time() - start_time)
    
    return output(
        service_name=kwargs.get("service_name", "unknown"),
        status="healthy",
        uptime_seconds=uptime,
    )
```

**SUB case (consume without output):**

```python
from fred_ops import FredOps
from datetime import datetime

app = FredOps()

@app.execute
async def execute(input, **kwargs):
    # Process message (no return)
    timestamp = datetime.fromtimestamp(input.timestamp).isoformat()
    
    print(f"[{timestamp}] Sensor {input.sensor_id}: {input.celsius}°C")
    
    # You can do here:
    # - Save to database
    # - Send email/SMS
    # - Optional: dashboard (Streamlit) and @app.storage — see fred-ops README
    # - Any side effect
```

### Best Practices

```python
# ✅ GOOD: Get parameters with default values
threshold = float(kwargs.get("threshold", 25.0))

# ❌ BAD: Assume parameter exists
threshold = float(kwargs["threshold"])  # KeyError if missing

# ✅ GOOD: Use clear and descriptive names
@app.execute
async def execute(input, output, **kwargs):
    ...

# ❌ BAD: Confusing names
@app.execute
async def execute(i, o, **k):
    ...

# ✅ GOOD: Exception handling
try:
    value = float(input.value)
except (ValueError, TypeError):
    value = 0.0

# ✅ GOOD: Use logging for debugging
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Processing: {input}")
```

---

## 5. Local Testing

### Step 5.1: Install fred-ops

If you haven't done so:

```bash
# From the monorepo root
uv pip install -e ./fred-ops
```

### Step 5.2: Have a local MQTT broker

Option A: Use Docker

```bash
docker run -d -p 1883:1883 eclipse-mosquitto:latest
```

Option B: Use your existing broker (edit `host` and `port` in `config/processor.yml`)

### Step 5.3: Generate test data

Create a script to publish test messages:

```python
# publish_test_data.py
import paho.mqtt.client as mqtt
import json
import time

client = mqtt.Client()
client.connect("localhost", 1883)
client.loop_start()

for i in range(5):
    msg = {
        "sensor_id": f"sensor_{i % 2}",
        "celsius": 20 + (i * 2),
        "timestamp": int(time.time()),
    }
    client.publish("sensors/temperature", json.dumps(msg))
    print(f"Published: {msg}")
    time.sleep(1)

client.loop_stop()
print("Done")
```

Run:

```bash
pip install paho-mqtt
python publish_test_data.py
```

### Step 5.4: Run the service

```bash
cd my-service
fred-ops run --config config/processor.yml --script src/processor.py
```

You should see:

```
2026-04-10 10:23:45 - Connected to MQTT
2026-04-10 10:23:46 - Subscribed to: sensors/temperature
2026-04-10 10:23:46 - Message received...
2026-04-10 10:23:46 - Published to: metrics/temperature
...
```

### Step 5.5: Verify output

Subscribe to the output topic in another terminal:

```bash
mosquitto_sub -h localhost -p 1883 -t "metrics/temperature"
```

You should see messages being published.

### Step 5.6: Debugging

#### View what's being published

Add debug to the config:

```bash
fred-ops run --config config/processor.yml --script src/processor.py --kwarg debug=true
```

#### Use print/logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.execute
async def execute(input, output, **kwargs):
    logger.debug(f"Input: {input}")
    logger.debug(f"Parameters: {kwargs}")
    # ... logic ...
    logger.debug(f"Output: {result}")
    return result
```

---

## 6. Deployment

### Option A: Docker Container

Create `Dockerfile`:

```dockerfile
FROM python:3.13-slim

RUN pip install uv

WORKDIR /app

# Copy fred-ops from the monorepo
COPY fred-ops/ /app/fred-ops/

# Copy your service
COPY my-service/ /app/my-service/

# Install fred-ops
RUN uv pip install -e /app/fred-ops

WORKDIR /app/my-service

CMD ["fred-ops", "run", "--config", "config/processor.yml", "--script", "src/processor.py"]
```

Build and run:

```bash
docker build -t my-service .
docker run -e MQTT_HOST=mqtt.example.com my-service
```

### Option B: Systemd Service

Create `/etc/systemd/system/my-service.service`:

```ini
[Unit]
Description=My Fred-ops Service
After=network.target

[Service]
Type=simple
User=fred-ops
WorkingDirectory=/opt/my-service
ExecStart=/path/to/venv/bin/fred-ops run --config config/processor.yml --script src/processor.py
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and run:

```bash
sudo systemctl enable my-service
sudo systemctl start my-service
sudo systemctl status my-service
```

View logs:

```bash
journalctl -u my-service -f
```

### Option C: Kubernetes

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-service
  template:
    metadata:
      labels:
        app: my-service
    spec:
      containers:
      - name: processor
        image: my-service:latest
        env:
        - name: MQTT_HOST
          value: "mqtt.default.svc.cluster.local"
        - name: MQTT_PORT
          value: "1883"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        restartPolicy: Always
```

Deploy:

```bash
kubectl apply -f k8s/deployment.yaml
```

---

## Verification Checklist

Before deploying:

- [ ] YAML configuration is valid (no syntax errors)
- [ ] All required fields in input/output
- [ ] `execute()` function is `async`
- [ ] Parameters in `kwargs` have default values
- [ ] Exception handling is correct
- [ ] Tested locally with real data
- [ ] Logs/debugging are configured
- [ ] Clear documentation about what the service does

---

## Complete Examples

### Service 1: JSON Validator

```
config/processor.yml:
mode: pubsub
input:
  topic: raw/messages
  schema:
    id: str
    data: str
output:
  topic: validated/messages
  schema:
    id: str
    valid: bool
    error: str

src/processor.py:
import json
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(input, output, **kwargs):
    try:
        json.loads(input.data)
        return output(id=input.id, valid=True, error="")
    except json.JSONDecodeError as e:
        return output(id=input.id, valid=False, error=str(e))
```

### Service 2: Event Counter

```
config/processor.yml:
mode: sub
input:
  topic: events/system
  schema:
    event_type: str
    timestamp: int

src/processor.py:
from collections import Counter
from fred_ops import FredOps

app = FredOps()
event_counter = Counter()

@app.execute
async def execute(input, **kwargs):
    event_counter[input.event_type] += 1
    print(f"Events counted: {dict(event_counter)}")
```

### Service 3: Metrics Generator

```
config/processor.yml:
mode: pub
output:
  topic: metrics/system
  schema:
    cpu_percent: float
    memory_percent: float
    timestamp: int

src/processor.py:
import psutil
import time
from fred_ops import FredOps

app = FredOps()

@app.execute
async def execute(output, **kwargs):
    return output(
        cpu_percent=psutil.cpu_percent(),
        memory_percent=psutil.virtual_memory().percent,
        timestamp=int(time.time()),
    )
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: fred_ops` | Run `uv pip install -e ./fred-ops` |
| `Connection refused` | Verify MQTT is running on `host:port` from config |
| `Validation error` | Ensure JSON types match the config |
| `No FredOps instance found` | Verify you have `app = FredOps()` and `@app.execute` |
| Messages not reaching output | Verify the topic is correctly written in config |

---

## Next Steps

1. **Testing:** Add unit tests in `tests/test_processor.py`
2. **Monitoring:** Configure logs and alerts
3. **Documentation:** Write a README for your service
4. **CI/CD:** Add the service to your pipeline (GitHub Actions, etc.)

Congratulations! You've created your first fred-ops service.
