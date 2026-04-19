import logging

from fred_ops import FredOps
from pydantic import ValidationError

from app.ener_vault_client import post_meter_reading
from app.models import MeterReading
from app.mqtt_topic import parse_energy_stats_meter_id

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FredOps()


@app.execute
async def execute(
    *,
    mqtt_topic: str,
    payload_json: dict | None,
    payload_bytes: bytes | None = None,
    **kwargs,
) -> None:
    payload = payload_json if payload_json is not None else payload_bytes
    logger.info("Received message (topic=%s) payload=%s", mqtt_topic, payload)
    return None


@app.storage
async def storage(
    *,
    mqtt_topic: str,
    payload_json: dict | None,
    payload_bytes: bytes | None = None,
    **kwargs,
) -> None:
    try:
        meter_id = parse_energy_stats_meter_id(mqtt_topic)
    except ValidationError as e:
        logger.error(
            "Skipping storage: could not extract meter_id from topic (topic=%s): %s",
            mqtt_topic,
            e,
        )
        return None

    if payload_json is None:
        logger.error(
            "Skipping storage: missing JSON payload (topic=%s)",
            mqtt_topic,
        )
        return None

    try:
        reading = MeterReading.model_validate(payload_json)
    except ValidationError as e:
        logger.error(
            "Skipping storage: could not validate payload (topic=%s): %s",
            mqtt_topic,
            e,
        )
        return None

    ok = await post_meter_reading(meter_id, reading)
    if ok:
        logger.info(
            "Stored measurement for device_id=%s (topic=%s)",
            meter_id,
            mqtt_topic,
        )
    return None
