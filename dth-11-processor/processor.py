import logging
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
        input: InputModel with valor, unidad, timestamp
        **kwargs: Additional parameters from config (part of fred-ops contract)
    """
    message = (
        f"Sensor Reading | "
        f"Value: {input.valor} {input.unidad} | "
        f"Timestamp: {input.timestamp}"
    )
    logger.info(message)
