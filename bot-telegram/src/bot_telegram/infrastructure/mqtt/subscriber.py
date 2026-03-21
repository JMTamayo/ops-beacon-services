from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt

if TYPE_CHECKING:
    from bot_telegram.infrastructure.config.settings import MqttSection

logger = logging.getLogger(__name__)


class MqttSubscriber:
    """Plain MQTT (no TLS) subscriber with a background network loop."""

    def __init__(
        self,
        mqtt_config: "MqttSection",
        on_payload: Callable[[bytes], None],
    ) -> None:
        self._cfg = mqtt_config
        self._on_payload = on_payload
        self.connected = False
        self._client = mqtt.Client(
            client_id="ops-beacon-telegram",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._client.username_pw_set(mqtt_config.username, mqtt_config.password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            logger.error("MQTT connect failed: %s", reason_code)
            self.connected = False
            return
        self.connected = True
        client.subscribe(self._cfg.topic)
        logger.info("MQTT subscribed to %s", self._cfg.topic)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        self.connected = False
        if reason_code.is_failure:
            logger.warning("MQTT disconnect: %s", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        raw_topic = msg.topic
        if isinstance(raw_topic, (bytes, bytearray)):
            topic_s = raw_topic.decode("utf-8", errors="replace")
        else:
            topic_s = str(raw_topic)
        logger.info(
            "MQTT message received topic=%s bytes=%s",
            topic_s,
            len(msg.payload),
        )
        self._on_payload(msg.payload)

    def start(self) -> None:
        self._client.connect(self._cfg.host, self._cfg.port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:
            logger.exception("Error while disconnecting MQTT client")
