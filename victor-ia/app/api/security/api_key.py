"""API key validation (bcrypt hash in config), aligned with JMTamayo/aura."""

from __future__ import annotations

import bcrypt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config.conf import CONFIG

_api_key_header = APIKeyHeader(
    name=CONFIG.SERVER_API_KEY_NAME,
    auto_error=False,
)


async def get_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Validate the API key header against the configured bcrypt hash."""

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Send the shared secret in the configured header (e.g. X-API-Key).",
        )
    if not bcrypt.checkpw(
        api_key.encode(),
        CONFIG.SERVER_API_KEY_VALUE_HASHED.get_secret_value().encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
