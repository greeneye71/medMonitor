"""MQTT client — subscribes to zigbee2mqtt/# and writes readings."""

import asyncio
import json
import logging
import time
from typing import Any, Callable

import paho.mqtt.client as mqtt

from backend.config import settings

logger = logging.getLogger(__name__)

# Exponential backoff parameters
RECONNECT_MIN = 1
RECONNECT_MAX = 60


class MQTTClient:
    """Paho-MQTT client with exponential backoff reconnection."""

    def __init__(self, on_reading: Callable[[dict[str, Any]], Any] | None = None) -> None:
        self._on_reading = on_reading
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._reconnect_delay = RECONNECT_MIN
        self._running = False

    def start(self) -> None:
        """Connect to MQTT broker and start loop in background thread."""
        host = settings.mqtt_host
        port = settings.mqtt_port
        logger.info("Connecting to MQTT broker %s:%d", host, port)
        try:
            self._client.connect(host, port, keepalive=60)
            self._running = True
            self._client.loop_start()
        except Exception as e:
            logger.error("MQTT initial connection failed: %s", e)
            self._schedule_reconnect()

    def stop(self) -> None:
        """Disconnect and stop MQTT loop."""
        self._running = False
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT client stopped")

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            logger.info("MQTT connected, subscribing to zigbee2mqtt/#")
            client.subscribe("zigbee2mqtt/#")
            self._reconnect_delay = RECONNECT_MIN
        else:
            logger.error("MQTT connection failed with code %d", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None) -> None:
        if self._running:
            logger.warning("MQTT disconnected (rc=%d), scheduling reconnect", rc)
            self._schedule_reconnect()

    def _on_message(self, client, userdata, msg) -> None:
        try:
            topic = msg.topic
            # Ignore bridge messages and non-device topics
            if "/bridge/" in topic or not msg.payload:
                return

            payload = json.loads(msg.payload.decode("utf-8"))

            # Only process messages with temperature data
            if "temperature" not in payload:
                return

            # Extract sensor_id from topic: zigbee2mqtt/0x00158d0001234567
            parts = topic.split("/")
            if len(parts) < 2:
                return
            sensor_id = parts[-1]

            reading = {
                "sensor_id": sensor_id,
                "zone": self._detect_zone(payload),
                "temperature": float(payload["temperature"]),
                "humidity": float(payload["humidity"]) if "humidity" in payload else None,
                "battery": int(payload["battery"]) if "battery" in payload else None,
            }

            logger.debug("Reading from %s: %.1f°C", sensor_id, reading["temperature"])

            if self._on_reading:
                self._on_reading(reading)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse MQTT message on %s: %s", msg.topic, e)

    def _schedule_reconnect(self) -> None:
        """Reconnect with exponential backoff in a separate thread."""
        import threading

        def _reconnect():
            logger.info("Reconnecting in %ds...", self._reconnect_delay)
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, RECONNECT_MAX)
            if not self._running:
                return
            try:
                self._client.reconnect()
            except Exception as e:
                logger.error("Reconnect failed: %s", e)
                if self._running:
                    self._schedule_reconnect()

        threading.Thread(target=_reconnect, daemon=True).start()

    @staticmethod
    def _detect_zone(payload: dict) -> str:
        """Heuristic zone detection based on temperature range."""
        temp = payload.get("temperature", 20.0)
        if temp < 0:
            return "freezer"
        return "fridge"
