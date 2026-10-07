"""MQTT client for zigbee2mqtt: updates sensors.last_* and tracks bridge state."""
import json
import logging
import math
import threading
from dataclasses import dataclass, field

import paho.mqtt.client as mqtt

from app.db import Database, iso, utcnow

log = logging.getLogger(__name__)

BASE = "zigbee2mqtt"


@dataclass
class BridgeState:
    online: bool = False
    version: str = ""
    devices: dict[str, str] = field(default_factory=dict)   # friendly_name -> ieee
    models: dict[str, str] = field(default_factory=dict)    # ieee -> model
    permit_join_until: float = 0.0


def _ieee_for(state: BridgeState, name: str) -> str | None:
    if name in state.devices:
        return state.devices[name]
    if name.startswith("0x"):          # default friendly_name is the ieee address
        return name
    return None


def handle_message(db: Database, state: BridgeState, topic: str, payload: bytes, now=None) -> None:
    """Apply one MQTT message. Never raises on bad payloads."""
    now = now or utcnow()
    if not topic.startswith(BASE + "/"):
        return
    sub = topic[len(BASE) + 1:]
    text = payload.decode("utf-8", errors="replace").strip()

    if sub == "bridge/state":
        try:
            value = json.loads(text)
            value = value.get("state") if isinstance(value, dict) else value
        except ValueError:
            value = text
        state.online = value == "online"
        return
    if sub.startswith("bridge/"):
        try:
            data = json.loads(text)
        except ValueError:
            return
        if sub == "bridge/info" and isinstance(data, dict):
            state.version = str(data.get("version", ""))
        elif sub == "bridge/devices" and isinstance(data, list):
            devices, models = {}, {}
            for d in data:
                if not isinstance(d, dict) or d.get("type") == "Coordinator":
                    continue
                ieee, name = d.get("ieee_address"), d.get("friendly_name")
                if not ieee or not name:
                    continue
                devices[name] = ieee
                model = (d.get("definition") or {}).get("model") or d.get("model_id") or ""
                models[ieee] = model
                db.execute(
                    "INSERT INTO discovered(ieee,friendly_name,model,first_seen) VALUES(?,?,?,?) "
                    "ON CONFLICT(ieee) DO UPDATE SET friendly_name=excluded.friendly_name, "
                    "model=excluded.model", (ieee, name, model, iso(now)))
            state.devices, state.models = devices, models
        return
    if "/" in sub:                      # e.g. <name>/set, <name>/availability
        return

    try:
        data = json.loads(text)
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    temp = data.get("temperature")
    if not isinstance(temp, (int, float)) or isinstance(temp, bool) or not math.isfinite(temp):
        return
    ieee = _ieee_for(state, sub)
    if ieee is None:
        return
    battery = data.get("battery")
    ok = isinstance(battery, (int, float)) and not isinstance(battery, bool) and math.isfinite(battery)
    battery = int(battery) if ok else None
    cur = db.execute(
        "UPDATE sensors SET last_temp=?, last_battery=COALESCE(?, last_battery), last_seen_at=? "
        "WHERE ieee=? AND active=1", (float(temp), battery, iso(now), ieee))
    if cur.rowcount == 0:
        db.execute(
            "INSERT INTO discovered(ieee,friendly_name,model,first_seen,last_temp) "
            "VALUES(?,?,?,?,?) ON CONFLICT(ieee) DO UPDATE SET last_temp=excluded.last_temp, "
            "friendly_name=excluded.friendly_name",
            (ieee, sub, state.models.get(ieee, ""), iso(now), float(temp)))
    else:
        db.execute("UPDATE discovered SET last_temp=? WHERE ieee=?", (float(temp), ieee))


class MqttService:
    def __init__(self, db: Database, host: str, port: int = 1883):
        self.db, self.host, self.port = db, host, port
        self.state = BridgeState()
        self.connected = False
        self._lock = threading.Lock()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="medmonitor")
        self.client.reconnect_delay_set(1, 60)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self) -> None:
        self.client.connect_async(self.host, self.port, keepalive=60)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = not reason_code.is_failure
        if self.connected:
            log.info("MQTT connesso a %s:%s", self.host, self.port)
            client.subscribe([(f"{BASE}/bridge/devices", 0), (f"{BASE}/bridge/state", 0),
                              (f"{BASE}/bridge/info", 0), (f"{BASE}/+", 0)])
        else:
            log.warning("MQTT connessione rifiutata: %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = False
        log.warning("MQTT disconnesso: %s", reason_code)

    def _on_message(self, client, userdata, msg):
        try:
            with self._lock:
                handle_message(self.db, self.state, msg.topic, msg.payload)
        except Exception:  # noqa: BLE001 - never kill the network thread
            log.exception("errore gestione messaggio %s", msg.topic)

    def publish(self, topic: str, data: dict) -> bool:
        if not self.connected:
            return False
        return self.client.publish(topic, json.dumps(data)).rc == mqtt.MQTT_ERR_SUCCESS

    def permit_join(self, seconds: int = 120) -> bool:
        return self.publish(f"{BASE}/bridge/request/permit_join", {"time": seconds})

    def remove_device(self, ieee: str) -> bool:
        return self.publish(f"{BASE}/bridge/request/device/remove", {"id": ieee, "force": True})

    def restart_bridge(self) -> bool:
        return self.publish(f"{BASE}/bridge/request/restart", {})
