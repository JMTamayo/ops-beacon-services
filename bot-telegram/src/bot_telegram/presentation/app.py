from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from bot_telegram.application.use_cases.forward_error_events import ForwardErrorEventsUseCase
from bot_telegram.infrastructure.mqtt.subscriber import MqttSubscriber
from bot_telegram.infrastructure.parsing.json_event_parser import JsonEventParser
from bot_telegram.infrastructure.telegram.notifier import TelegramNotifier

if TYPE_CHECKING:
    from bot_telegram.infrastructure.config.settings import ServiceConfig

logger = logging.getLogger(__name__)


class TelegramExampleResponse(BaseModel):
    """Respuesta de POST /telegram/example."""

    status: str = Field(examples=["sent"])
    detail: str = Field(description="Descripción breve del resultado")


def build_app(config: "ServiceConfig") -> FastAPI:
    parser = JsonEventParser()
    notifier = TelegramNotifier(config.telegram.bot_token, config.telegram.chat_id)
    use_case = ForwardErrorEventsUseCase(parser, notifier)

    def _on_mqtt_payload(payload: bytes) -> None:
        try:
            use_case.handle_payload(payload)
        except Exception:
            logger.exception("Failed to handle MQTT payload")

    mqtt = MqttSubscriber(config.mqtt, _on_mqtt_payload)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        mqtt.start()
        app.state.service_config = config
        app.state.mqtt = mqtt
        app.state.notifier = notifier
        yield
        notifier.close()
        mqtt.stop()

    app = FastAPI(
        title="Ops Beacon Telegram",
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "health",
                "description": "Estado del proceso y del cliente MQTT.",
            },
            {
                "name": "config",
                "description": "Configuración cargada (secretos enmascarados).",
            },
            {
                "name": "telegram",
                "description": "Pruebas del Bot API sin usar MQTT.",
            },
        ],
    )

    @app.get("/health", tags=["health"])
    def health(request: Request) -> Response:
        m = request.app.state.mqtt
        if m.connected:
            return Response(status_code=204)
        return Response(status_code=503)

    @app.get("/config", tags=["config"])
    def get_config(request: Request) -> dict[str, Any]:
        cfg: ServiceConfig = request.app.state.service_config
        return cfg.to_public_json()

    @app.post(
        "/telegram/example",
        response_model=TelegramExampleResponse,
        tags=["telegram"],
        summary="Enviar mensaje de prueba a Telegram",
        description=(
            "Usa `bot_token` y `chat_id` del YAML. "
            "Sirve para validar credenciales sin pasar por MQTT."
        ),
    )
    def post_telegram_example(request: Request) -> TelegramExampleResponse:
        notifier: TelegramNotifier = request.app.state.notifier
        try:
            notifier.send_example_message()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Telegram API responded with an error: {exc.response.text!r}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach Telegram API: {exc!s}",
            ) from exc
        return TelegramExampleResponse(
            status="sent",
            detail="Mensaje de ejemplo enviado al chat configurado.",
        )

    return app


def create_app() -> FastAPI:
    from bot_telegram.presentation.bootstrap import load_runtime_config

    return build_app(load_runtime_config())
