"""RFC 7807 Problem Details (application/problem+json)."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.conf import CONFIG


def _type_uri(suffix: str) -> str:
    base = CONFIG.PROBLEM_TYPE_URI_PREFIX.rstrip("/")
    return f"{base}/{suffix}"


def problem_json_response(
    *,
    status_code: int,
    title: str | None,
    detail: str,
    type_suffix: str,
    instance: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build a JSONResponse with Content-Type application/problem+json."""

    if title is None:
        title = HTTPStatus(status_code).phrase
    body: dict[str, Any] = {
        "type": _type_uri(type_suffix),
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance is not None:
        body["instance"] = instance
    if extensions:
        body.update(extensions)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )


def problem_for_request(
    request: Request,
    *,
    status_code: int,
    title: str | None,
    detail: str,
    type_suffix: str,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    """Problem response with RFC 7807 `instance` set to the request path."""

    return problem_json_response(
        status_code=status_code,
        title=title,
        detail=detail,
        type_suffix=type_suffix,
        instance=request.url.path,
        extensions=extensions,
    )
