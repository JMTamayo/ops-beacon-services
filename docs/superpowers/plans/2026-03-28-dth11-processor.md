# dth-11-processor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reusable DHT11 sensor processor template that receives MQTT messages and logs them to console using fred-ops framework.

**Architecture:** A minimal SUB-mode processor with YAML config and Python execute function. Config defines MQTT broker, topic, and message schema. The processor logs each received sensor reading with timestamp, device ID, temperature, and humidity.

**Tech Stack:** fred-ops (MQTT + async), PyYAML (config), Python 3.12+, standard logging module

---

### Task 1: Create dth-11-processor directory and config.yml

**Files:**
- Create: `dth-11-processor/config.yml`

- [ ] **Step 1: Create directory**

```bash
mkdir -p dth-11-processor
```

- [ ] **Step 2: Create config.yml with broker and SUB mode configuration**

```bash
cat > dth-11-processor/config.yml << 'EOF'
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
EOF
```

- [ ] **Step 3: Verify config.yml was created**

```bash
cat dth-11-processor/config.yml
```

Expected output:
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

---

### Task 2: Create processor.py with FredOps instance and execute function

**Files:**
- Create: `dth-11-processor/processor.py`

- [ ] **Step 1: Create processor.py with imports and FredOps instance**

```bash
cat > dth-11-processor/processor.py << 'EOF'
import logging
from datetime import datetime
from fred_ops import FredOps

# Configure logging to show messages in console
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FredOps()


@app.execute
async def execute(input, **kwargs) -> None:
    """
    Receive DHT11 sensor readings and log to console.

    Args:
        input: InputModel with device_id, temperature, humidity
        **kwargs: Additional parameters from config
    """
    message = (
        f"Device: {input.device_id} | "
        f"Temp: {input.temperature}°C | "
        f"Humidity: {input.humidity}%"
    )
    logger.info(message)
EOF
```

- [ ] **Step 2: Verify processor.py was created**

```bash
cat dth-11-processor/processor.py
```

Expected output: Shows complete processor with logging setup and execute function.

---

### Task 3: Update Makefile to add run-dth11 target

**Files:**
- Modify: `Makefile` (add .PHONY and new target)

- [ ] **Step 1: Add dth11 to .PHONY declaration**

Edit `Makefile` line 4:
```makefile
.PHONY: help up up-build down down-v build logs logs-bot ps restart stop start pull run-dth11
```

- [ ] **Step 2: Add run-dth11 target and update help message**

Add after line 22 (after `make pull` help text) in help target:
```makefile
	@echo "  make run-dth11   - Run dth-11 processor (requires MQTT broker at localhost:1883)"
```

- [ ] **Step 3: Add run-dth11 target at end of Makefile**

Add after line 58 (after pull target):
```makefile
run-dth11:
	cd dth-11-processor && fred-ops run --config config.yml --script processor.py
```

- [ ] **Step 4: Verify Makefile syntax is correct**

```bash
make help
```

Expected output: New `make run-dth11` entry visible in help output.

---

### Task 4: Commit all changes

**Files:**
- `dth-11-processor/config.yml`
- `dth-11-processor/processor.py`
- `Makefile`

- [ ] **Step 1: Check git status**

```bash
git status
```

Expected: Shows 3 files (config.yml, processor.py, modified Makefile).

- [ ] **Step 2: Stage all changes**

```bash
git add dth-11-processor/config.yml dth-11-processor/processor.py Makefile
```

- [ ] **Step 3: Create commit**

```bash
git commit -m "feat: add dth-11-processor template with SUB mode and console logging

- Create dth-11-processor directory with YAML config
- Config defines sensor/dth11 MQTT topic with temperature/humidity/device_id schema
- Processor uses fred-ops SUB mode to receive and log readings to console
- Add 'make run-dth11' target to Makefile for convenience"
```

- [ ] **Step 4: Verify commit**

```bash
git log --oneline -1
```

Expected: Shows new commit with feature message.
