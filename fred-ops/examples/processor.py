"""
Example fred-ops processor (PUBSUB mode).

Run with:
    fred-ops run --config examples/config_pubsub.yml --script examples/processor.py
"""
from fred_ops import FredOps

app = FredOps()


@app.execute
async def execute(input, output, **kwargs):
    threshold = float(kwargs.get("threshold", 25.0))
    return output(
        device_id=input.device_id,
        alert=input.temperature > threshold,
    )
