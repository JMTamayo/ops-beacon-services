from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.router import server_router
from app.config.conf import CONFIG
from app.http.problem import problem_for_request

logger = logging.getLogger(__name__)

app = FastAPI(
    title=CONFIG.SERVER_API_NAME,
    description=CONFIG.SERVER_API_DESCRIPTION,
    version=CONFIG.SERVER_API_VERSION,
)

app.include_router(server_router)


def _problem_suffix_for_status(status_code: int) -> str:
    return {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        422: "validation-error",
        502: "bad-gateway",
        500: "internal-server-error",
    }.get(status_code, "error")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    status_code = exc.status_code
    raw = exc.detail
    if isinstance(raw, str):
        detail = raw
    elif isinstance(raw, list):
        detail = "; ".join(str(x) for x in raw)
    else:
        detail = str(raw)
    title = HTTPStatus(status_code).phrase
    return problem_for_request(
        request,
        status_code=status_code,
        title=title,
        detail=detail,
        type_suffix=_problem_suffix_for_status(status_code),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return problem_for_request(
        request,
        status_code=422,
        title="Validation error",
        detail="The request does not match the expected JSON schema.",
        type_suffix="validation-error",
        extensions={"errors": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return problem_for_request(
        request,
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected error occurred.",
        type_suffix="internal-server-error",
    )
