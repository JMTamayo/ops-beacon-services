from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("config/.env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVER_API_NAME: str = "ener-vault"
    SERVER_API_DESCRIPTION: str = "CRUD API for energy meter measurements."
    SERVER_API_VERSION: str = "0.1.0"

    DATABASE_URL: str


CONFIG = Settings()
