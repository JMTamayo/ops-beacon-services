from enum import Enum


class EventStatus(str, Enum):
    """Lifecycle state aligned with ops-beacon domain."""

    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"

    @classmethod
    def from_string(cls, value: str) -> "EventStatus":
        upper = value.strip().upper()
        for member in cls:
            if member.value == upper:
                return member
        raise ValueError(f"Unknown event status: {value!r}")
