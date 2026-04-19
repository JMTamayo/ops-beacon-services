from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError


def _topic_validation_error(topic: str, message: str) -> ValidationError:
    return ValidationError.from_exception_data(
        "parse_energy_stats_meter_id",
        [
            {
                "type": "value_error",
                "loc": ("topic",),
                "input": topic,
                "ctx": {"error": ValueError(message)},
            }
        ],
    )


def parse_energy_stats_meter_id(topic: str) -> UUID:
    """Return meter_id from topics shaped like `/volttio/<meter_id>/energy-stats`.

    `meter_id` must be a UUID string. Leading/trailing slashes are tolerated.

    Raises:
        ValidationError: if the topic shape is wrong or `meter_id` is not a UUID.
    """
    parts = [p for p in topic.split("/") if p]
    if len(parts) != 3:
        raise _topic_validation_error(
            topic,
            "Topic must have shape /volttio/<meter_id>/energy-stats",
        )
    root, meter_id, suffix = parts
    if root != "volttio" or suffix != "energy-stats":
        raise _topic_validation_error(
            topic,
            "Topic must start with volttio/ and end with /energy-stats",
        )
    try:
        return UUID(meter_id)
    except ValueError as e:
        raise _topic_validation_error(topic, "meter_id must be a valid UUID") from e
