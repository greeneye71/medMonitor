"""MQTT client — subscribes to zigbee2mqtt/# and writes readings."""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine

import paho.mqtt.client as mqtt

from backend.config import settings
from backend.paths import data_file

logger = logging.getLogger(__name__)

# Exponential backoff parameters
RECONNECT_MIN = 1
RECONNECT_MAX = 60

_SENSORS_FILE = data_file("sensors.json")


def _load_sensors_registry() -> dict[str, dict]:
    """Load sensors registry from sensors.json.

    Returns {sensor_id: {"zone": ..., "name": ..., "active": ...}}.
    Used for zone lookup — avoids misclassifying sensors in alarm states.
    """
    if _SENSORS_FILE.exists():
        try:
            return json.loads(_SENSORS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class MQTTClient:
    """Paho-MQTT client with exponential backoff reconnection.

    The on_reading callback must be an async coroutine.  It is scheduled
    onto the provided asyncio event loop from Paho's background thread via
    asyncio.run_coroutine_threadsafe(), so it never blocks the MQTT thread
    and never creates asyncio runtime conflicts.
    """

    def __init__(
        self,
        on_reading: Callable[[dict[str, Any]], Coroutine] | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._on_reading = on_reading
        self._loop = loop
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._reconnect_delay = RECONNECT_MIN
        self._running = False
        self.health_state: str = "connecting"   # "connected"|"connecting"|"disconnected"|"error"
        self.discovered_sensors: set[str] = set()
        self._connected_at: float | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """True while the client is running (connected or reconnecting)."""
        return self._running

    @property
    def uptime_s(self) -> int:
        if self._connected_at is None:
            return 0
        return int(time.time() - self._connected_at)

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Connect to broker and start background MQTT loop thread."""
        if loop:
            self._loop = loop
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

    # ------------------------------------------------------------------
    # Paho callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            logger.info("MQTT connected, subscribing to zigbee2mqtt/#")
            client.subscribe("zigbee2mqtt/#")
            self._reconnect_delay = RECONNECT_MIN
            self.health_state = "connected"
            self._connected_at = time.time()
        else:
            logger.error("MQTT connection failed with code %d", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None) -> None:
        self.health_state = "disconnected"
        self._connected_at = None
        if self._running:
            logger.warning("MQTT disconnected (rc=%d), scheduling reconnect", rc)
            self._schedule_reconnect()

    def _on_message(self, client, userdata, msg) -> None:
        """Called from Paho's background thread. Schedules the async callback."""
        try:
            topic = msg.topic
            # Ignore bridge management messages and empty payloads
            if "/bridge/" in topic or not msg.payload:
                return

            payload = json.loads(msg.payload.decode("utf-8"))

            # Only process messages that carry temperature data
            if "temperature" not in payload:
                return

            # Extract sensor_id from topic: zigbee2mqtt/0x00158d0001234567
            parts = topic.split("/")
            if len(parts) < 2:
                return
            sensor_id = parts[-1]
            self.discovered_sensors.add(sensor_id)

            temp = float(payload["temperature"])
            reading = {
                "sensor_id": sensor_id,
                "zone": self._get_zone(sensor_id, temp=temp),
                "temperature": temp,
                "humidity": float(payload["humidity"]) if "humidity" in payload else None,
                "battery": int(payload["battery"]) if "battery" in payload else None,
            }

            logger.debug(
                "Reading from %s: %.1f°C zone=%s",
                sensor_id, temp, reading["zone"],
            )

            # Schedule async callback on the asyncio event loop from this thread
            if self._on_reading and self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._on_reading(reading), self._loop
                )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse MQTT message on %s: %s", msg.topic, e)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_zone(self, sensor_id: str, temp: float = 20.0) -> str:
        """Return zone for a sensor.

        Primary source: sensors.json registry (set by operator via UI).
        Fallback: temperature heuristic for unknown/unregistered sensors.
        Using only temperature is wrong for sensors in alarm state (e.g. a
        freezer warming to +5°C would be misclassified as fridge).
        """
        registry = _load_sensors_registry()
        entry = registry.get(sensor_id)
        if entry:
            return entry.get("zone", "fridge")
        # Heuristic for new/unregistered sensors
        return "freezer" if temp < 0 else "fridge"

    def _schedule_reconnect(self) -> None:
        """Exponential backoff reconnect in a separate daemon thread."""
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
