from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bot_telegram.infrastructure.config.settings import ServiceConfig, load_service_config


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )
    config_path: Path = Field(
        default=Path("config/config.yaml"),
        description="Path to YAML configuration file",
        alias="CONFIG_PATH",
    )


def load_runtime_config() -> ServiceConfig:
    env = EnvSettings()
    return load_service_config(env.config_path)
