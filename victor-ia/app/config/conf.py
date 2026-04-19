"""Application settings (env + pyproject metadata)."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT / "config" / ".env"


class PyProjectMeta:
    """Name, description, version from pyproject.toml."""

    PROJECT_NAME: str
    PROJECT_DESCRIPTION: str
    PROJECT_VERSION: str

    def __init__(self) -> None:
        with open(_ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        proj = data["project"]
        self.PROJECT_NAME = "Victor IA"
        self.PROJECT_DESCRIPTION = str(proj["description"])
        self.PROJECT_VERSION = str(proj["version"])


_meta = PyProjectMeta()


class Config(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVER_API_NAME: str = _meta.PROJECT_NAME
    SERVER_API_DESCRIPTION: str = _meta.PROJECT_DESCRIPTION
    SERVER_API_VERSION: str = _meta.PROJECT_VERSION

    # Header name (e.g. X-API-Key) and bcrypt hash of the plain API key (see aura).
    SERVER_API_KEY_NAME: str = "X-API-Key"
    SERVER_API_KEY_VALUE_HASHED: SecretStr

    # RFC 7807 Problem Details: base URI for the `type` field (suffix appended per case).
    PROBLEM_TYPE_URI_PREFIX: str = "https://ops-beacon.invalid/problems"

    ENER_VAULT_BASE_URL: str = "http://ener-vault:8080"

    # Power Automate HTTP trigger → Teams canal del equipo de operación (query contiene sig — secreto).
    TEAMS_WEBHOOK_URL: SecretStr | None = None

    LLM_PROVIDER: str = "google_genai"
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = 0.2
    LLM_API_KEY: SecretStr


CONFIG: Config = Config()
