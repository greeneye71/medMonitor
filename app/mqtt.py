"""MQTT client for zigbee2mqtt: updates sensors.last_* and tracks bridge state."""
import json
import logging
import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from app.db import Database, iso, parse, utcnow
from app.gateways import Gateway, by_id

log = logging.getLogger(__name__)

@dataclass
class BridgeState:
    online: bool = False
    version: str = ""
    devices: dict[str, str] = field(default_factory=dict)   # friendly_name -> ieee
    models: dict[str, str] = field(default_factory=dict)    # ieee -> model
    permit_join_until: float = 0.0
    online_since: datetime | None = None
    offline_since: datetime | None = None


def _ieee_for(state: BridgeState, name: str) -> str | None:
    if name in state.devices:
        return state.devices[name]
    if name.startswith("0x"):          # default friendly_name is the ieee address
        return name
    return None


def _seen_at(value, now: datetime) -> datetime:
    """When the sensor really spoke: z2m `last_seen` (ISO_8601 or epoch ms), else `now`.

    z2m republishes its state cache at startup (cache_state_send_on_startup): without this,
    a sensor silent for days would look online with a stale temperature.
    """
    seen = None
    if isinstance(value, str):
        try:
            seen = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        try:
            seen = datetime.fromtimestamp(value / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass
    if seen is None:
        return now
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return min(seen.replace(microsecond=0), now)


def _gateway_for(gateways: list[Gateway], topic: str) -> Gateway | None:
    """Gateway whose base topic prefixes `topic` (longest match: zigbee2mqtt_2 != zigbee2mqtt)."""
    hits = [g for g in gateways if topic.startswith(g.base_topic + "/")]
    return max(hits, key=lambda g: len(g.base_topic)) if hits else None


def _gw_name(gateways: list[Gateway], gid) -> str:
    gw = by_id(gateways, gid)
    return gw.name if gw else f"Gateway {gid}"


def handle_message(db: Database, states: dict[int, BridgeState], gateways: list[Gateway],
                   topic: str, payload: bytes, now=None, on_moved=None) -> None:
    """Apply one MQTT message. Never raises on bad payloads.

    `on_moved(old_gid, ieee)` is called when a registered sensor shows up on another gateway.
    """
    now = now or utcnow()
    gw = _gateway_for(gateways, topic)
    if gw is None or gw.id not in states:
        return
    gid, state = gw.id, states[gw.id]
    sub = topic[len(gw.base_topic) + 1:]
    text = payload.decode("utf-8", errors="replace").strip()

    if sub == "bridge/state":
        try:
            value = json.loads(text)
            value = value.get("state") if isinstance(value, dict) else value
        except ValueError:
            value = text
        online = value == "online"
        if state.online and not online:
            state.offline_since = now
        elif online and not state.online:
            state.online_since = now
            db.execute("INSERT INTO gateway_state(gateway_id, back_at) VALUES(?,?) "
                       "ON CONFLICT(gateway_id) DO UPDATE SET back_at=excluded.back_at",
                       (gid, iso(now)))
        state.online = online
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
                    "INSERT INTO discovered(ieee,friendly_name,model,first_seen,gateway_id) "
                    "VALUES(?,?,?,?,?) ON CONFLICT(ieee) DO UPDATE SET "
                    "friendly_name=excluded.friendly_name, model=excluded.model, "
                    "gateway_id=excluded.gateway_id", (ieee, name, model, iso(now), gid))
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
    seen_dt = _seen_at(data.get("last_seen"), now)
    seen = iso(seen_dt)
    sensor = db.one("SELECT name, gateway_id, last_seen_at FROM sensors WHERE ieee=? AND active=1",
                    (ieee,))
    if sensor is None:
        db.execute(
            "INSERT INTO discovered(ieee,friendly_name,model,first_seen,last_temp,last_seen,"
            "gateway_id) VALUES(?,?,?,?,?,?,?) ON CONFLICT(ieee) DO UPDATE SET "
            "last_temp=excluded.last_temp, last_seen=excluded.last_seen, "
            "friendly_name=excluded.friendly_name, gateway_id=excluded.gateway_id",
            (ieee, sub, state.models.get(ieee, ""), iso(now), float(temp), seen, gid))
        return
    old_gid = sensor["gateway_id"]
    if old_gid != gid:
        # Another gateway's cached state (cache_state_send_on_startup) can be older than what
        # we know: only a newer reading proves the sensor really moved.
        last = parse(sensor["last_seen_at"])
        if last is not None and seen_dt <= last:
            return
        db.add_event(now, ieee, "SENSOR_MOVED", f"{sensor['name']}: da "
                     f"{_gw_name(gateways, old_gid)} a {_gw_name(gateways, gid)}")
    db.execute(
        "UPDATE sensors SET last_temp=?, last_battery=COALESCE(?, last_battery), last_seen_at=?, "
        "gateway_id=? WHERE ieee=? AND active=1", (float(temp), battery, seen, gid, ieee))
    db.execute("UPDATE discovered SET last_temp=?, last_seen=?, gateway_id=? WHERE ieee=?",
               (float(temp), seen, gid, ieee))
    if old_gid != gid and on_moved and old_gid is not None:
        on_moved(old_gid, ieee)


class MqttService:
    def __init__(self, db: Database, host: str, port: int = 1883,
                 gateways: list[Gateway] | None = None):
        self.db, self.host, self.port = db, host, port
        self.gateways = gateways or [Gateway(1, "Gateway 1", "zigbee2mqtt", "")]
        self.states = {g.id: BridgeState() for g in self.gateways}
        self.started_at = utcnow()
        self.connected = False
        self._lock = threading.Lock()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="medmonitor")
        self.client.reconnect_delay_set(1, 60)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    @property
    def state(self) -> BridgeState:
        """First gateway's state (single-gateway callers)."""
        return self.states[self.gateways[0].id]

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
            topics = []
            for g in self.gateways:
                b = g.base_topic
                topics += [(f"{b}/bridge/devices", 0), (f"{b}/bridge/state", 0),
                           (f"{b}/bridge/info", 0), (f"{b}/+", 0)]
            client.subscribe(topics)
        else:
            log.warning("MQTT connessione rifiutata: %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.connected = False
        log.warning("MQTT disconnesso: %s", reason_code)

    def _on_message(self, client, userdata, msg):
        try:
            with self._lock:
                handle_message(self.db, self.states, self.gateways, msg.topic, msg.payload,
                               on_moved=self.remove_device)
        except Exception:  # noqa: BLE001 - never kill the network thread
            log.exception("errore gestione messaggio %s", msg.topic)

    def publish(self, topic: str, data: dict) -> bool:
        if not self.connected:
            return False
        return self.client.publish(topic, json.dumps(data)).rc == mqtt.MQTT_ERR_SUCCESS

    def _request(self, gid: int, what: str, data: dict) -> bool:
        gw = by_id(self.gateways, gid)
        return bool(gw) and self.publish(f"{gw.base_topic}/bridge/request/{what}", data)

    def permit_join(self, gid: int, seconds: int = 120) -> bool:
        return self._request(gid, "permit_join", {"time": seconds})

    def remove_device(self, gid: int, ieee: str) -> bool:
        return self._request(gid, "device/remove", {"id": ieee, "force": True})

    def restart_bridge(self, gid: int) -> bool:
        return self._request(gid, "restart", {})
