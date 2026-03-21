from enum import Enum


class AlertLevel(str, Enum):
    """Severity aligned with ops-beacon domain."""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def from_string(cls, value: str) -> "AlertLevel":
        upper = value.strip().upper()
        for member in cls:
            if member.value == upper:
                return member
        raise ValueError(f"Unknown alert level: {value!r}")
