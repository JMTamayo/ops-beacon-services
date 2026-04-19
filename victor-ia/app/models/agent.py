"""HTTP contract for Victor IA (success JSON + RFC 7807 errors via handlers)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VictorIAChatRequest(BaseModel):
    """Inbound chat message (Shortcuts-friendly: single `message` string)."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="User text for the agent.",
        examples=["List devices in ener-vault"],
    )

    @field_validator("message")
    @classmethod
    def strip_and_reject_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("message must not be empty or whitespace-only")
        return s


class VictorIAChatResponse(BaseModel):
    """Successful assistant reply (aligned with common chat-style JSON)."""

    role: Literal["assistant"] = "assistant"
    content: str = Field(..., description="Assistant reply text.")
