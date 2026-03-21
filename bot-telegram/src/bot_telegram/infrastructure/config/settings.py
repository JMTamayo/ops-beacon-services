from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class MqttSection(BaseModel):
    host: str
    port: int = 1883
    username: str
    password: str
    topic: str


class TelegramSection(BaseModel):
    bot_token: str
    chat_id: str

    @field_validator("chat_id", mode="before")
    @classmethod
    def chat_id_as_string(cls, value: object) -> str:
        return str(value)


class AppSection(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class ServiceConfig(BaseModel):
    mqtt: MqttSection
    telegram: TelegramSection
    app: AppSection = Field(default_factory=AppSection)

    def to_public_json(self) -> dict[str, Any]:
        """Configuration safe to expose over HTTP (secrets masked)."""
        return {
            "mqtt": {
                "host": self.mqtt.host,
                "port": self.mqtt.port,
                "username": self.mqtt.username,
                "password": "***",
                "topic": self.mqtt.topic,
            },
            "telegram": {
                "bot_token": "***",
                "chat_id": self.telegram.chat_id,
            },
            "app": self.app.model_dump(),
        }


def load_service_config(path: Path) -> ServiceConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "Configuration root must be a mapping"
        raise ValueError(msg)
    return ServiceConfig.model_validate(raw)
