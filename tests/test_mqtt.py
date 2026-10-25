import json

from datetime import datetime, timezone

from app.gateways import Gateway
from app.mqtt import BridgeState, handle_message
from tests.conftest import add_sensor

DEVICES = [
    {"ieee_address": "0x00", "friendly_name": "Coordinator", "type": "Coordinator"},
    {"ieee_address": "0x01", "friendly_name": "frigo_farmacia", "type": "EndDevice",
     "definition": {"model": "SNZB-02LD"}},
    {"ieee_address": "0x02", "friendly_name": "nuovo", "type": "EndDevice",
     "definition": {"model": "SNZB-02LD"}},
]


GW1 = [Gateway(1, "Gateway 1", "zigbee2mqtt", "c1")]
GW2 = GW1 + [Gateway(2, "Cucina", "zigbee2mqtt_2", "c2", 8081)]


def msg(db, states, topic, data, gws=GW1, base="zigbee2mqtt", **kw):
    raw = data if isinstance(data, bytes) else json.dumps(data).encode()
    handle_message(db, states, gws, base + "/" + topic, raw, **kw)


def test_devices_map_skips_coordinator(db):
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    assert st.devices == {"frigo_farmacia": "0x01", "nuovo": "0x02"}
    assert st.models["0x01"] == "SNZB-02LD"


def test_registered_sensor_updates_last(db):
    add_sensor(db, ieee="0x01", last_temp=None, last_battery=None)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "frigo_farmacia", {"temperature": 4.3, "battery": 87, "linkquality": 100})
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 4.3 and s["last_battery"] == 87 and s["last_seen_at"]
    msg(db, sts, "frigo_farmacia", {"temperature": 4.5})       # battery missing: keep old
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 4.5 and s["last_battery"] == 87


def test_unregistered_goes_to_discovered(db):
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "nuovo", {"temperature": 6.1, "battery": 100})
    d = db.one("SELECT * FROM discovered WHERE ieee='0x02'")
    assert d["last_temp"] == 6.1 and d["model"] == "SNZB-02LD"


def test_bad_payloads_ignored(db):
    add_sensor(db, ieee="0x01", last_temp=5.0, last_seen_at=None)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "frigo_farmacia", b"not json{")
    msg(db, sts, "frigo_farmacia", {"battery": 50})
    msg(db, sts, "frigo_farmacia", {"temperature": "hot"})
    msg(db, sts, "frigo_farmacia", [1, 2])
    msg(db, sts, "bridge/devices", b"garbage")
    msg(db, sts, "sconosciuto", {"temperature": 3})
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 5.0 and s["last_seen_at"] is None
    assert st.devices["frigo_farmacia"] == "0x01"


def test_bridge_state_and_info(db):
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/state", {"state": "online"})
    assert st.online
    msg(db, sts, "bridge/state", b"offline")
    assert not st.online
    msg(db, sts, "bridge/state", b"online")
    assert st.online
    msg(db, sts, "bridge/info", {"version": "2.1.0"})
    assert st.version == "2.1.0"


def test_ieee_friendly_name_fallback(db):
    add_sensor(db, ieee="0xabc", last_temp=None)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "0xabc", {"temperature": -18.2})
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == -18.2


def test_non_finite_values_ignored(db):
    add_sensor(db, ieee="0x01", last_temp=5.0, last_battery=90)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "frigo_farmacia", b'{"temperature": NaN}')
    msg(db, sts, "frigo_farmacia", b'{"temperature": Infinity}')
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == 5.0
    msg(db, sts, "frigo_farmacia", b'{"temperature": 4.0, "battery": NaN}')
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 4.0 and s["last_battery"] == 90


def test_inactive_sensor_goes_to_discovered(db):
    add_sensor(db, ieee="0x01", last_temp=5.0, active=0)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "frigo_farmacia", {"temperature": 3.3})
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == 5.0
    assert db.one("SELECT last_temp FROM discovered WHERE ieee='0x01'")["last_temp"] == 3.3


def test_discovered_records_last_seen(db):
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "nuovo", {"temperature": 6.1})
    d = db.one("SELECT first_seen, last_seen FROM discovered WHERE ieee='0x02'")
    assert d["last_seen"] is not None and d["last_seen"] >= d["first_seen"]


def test_cached_state_keeps_real_last_seen(db):
    # z2m republishes its state cache at startup: the payload's last_seen is the real
    # time the sensor spoke, not the time we received the message.
    from datetime import datetime, timezone
    add_sensor(db, ieee="0x01", last_temp=None, last_battery=None, last_seen_at=None)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    now = datetime(2026, 10, 13, 12, 25, tzinfo=timezone.utc)
    handle_message(db, sts, GW1, "zigbee2mqtt/frigo_farmacia", json.dumps(
        {"temperature": 24.9, "last_seen": "2026-10-09T09:41:12.356Z"}).encode(), now=now)
    s = db.one("SELECT * FROM sensors")
    assert s["last_seen_at"] == "2026-10-09T09:41:12+00:00"
    d = db.one("SELECT last_seen FROM discovered WHERE ieee='0x01'")
    assert d is None or d["last_seen"] == "2026-10-09T09:41:12+00:00"


def test_last_seen_epoch_future_and_garbage(db):
    from datetime import datetime, timezone
    add_sensor(db, ieee="0x01", last_temp=None, last_battery=None, last_seen_at=None)
    sts = {1: BridgeState()}
    st = sts[1]
    msg(db, sts, "bridge/devices", DEVICES)
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)

    def seen(last_seen):
        handle_message(db, sts, GW1, "zigbee2mqtt/frigo_farmacia", json.dumps(
            {"temperature": 4.0, "last_seen": last_seen}).encode(), now=now)
        return db.one("SELECT last_seen_at FROM sensors")["last_seen_at"]

    assert seen(int(datetime(2026, 10, 13, 11, 0, tzinfo=timezone.utc).timestamp() * 1000)) \
        == "2026-10-13T11:00:00+00:00"                          # epoch ms
    assert seen("2026-10-13T13:00:00Z") == "2026-10-13T12:00:00+00:00"   # future: clamp to now
    assert seen("garbage") == "2026-10-13T12:00:00+00:00"                # unparseable: now
    assert seen(True) == "2026-10-13T12:00:00+00:00"


def states2():
    return {1: BridgeState(), 2: BridgeState()}


def test_two_bases_routed(db):
    sts = states2()
    msg(db, sts, "bridge/state", b"online", gws=GW2, base="zigbee2mqtt_2")
    assert sts[2].online and not sts[1].online


def test_prefix_not_confused(db):
    sts = {1: BridgeState()}
    add_sensor(db, ieee="0xabc", last_temp=5.0)
    msg(db, sts, "0xabc", {"temperature": 3.0}, base="zigbee2mqtt_2")   # gw2 not registered
    msg(db, sts, "bridge/state", b"online", base="zigbee2mqtt_2")
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == 5.0
    assert not sts[1].online


def test_discovered_gets_gateway_id(db):
    sts = states2()
    msg(db, sts, "bridge/devices", DEVICES, gws=GW2, base="zigbee2mqtt_2")
    assert db.one("SELECT gateway_id FROM discovered WHERE ieee='0x01'")["gateway_id"] == 2
    msg(db, sts, "0x09", {"temperature": 6.0}, gws=GW2, base="zigbee2mqtt_2")
    assert db.one("SELECT gateway_id FROM discovered WHERE ieee='0x09'")["gateway_id"] == 2


def _move(db, sts, moved):
    add_sensor(db, ieee="0x01", name="Frigo 1", last_temp=5.0,
               last_seen_at="2026-10-13T10:00:00+00:00", gateway_id=1)
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    msg(db, sts, "0x01", {"temperature": 4.0, "last_seen": "2026-10-13T12:00:00Z"},
        gws=GW2, base="zigbee2mqtt_2", now=now,
        on_moved=lambda old, ieee: moved.append((old, ieee)))


def test_sensor_moved(db):
    sts, moved = states2(), []
    _move(db, sts, moved)
    s = db.one("SELECT * FROM sensors")
    assert s["gateway_id"] == 2 and s["last_temp"] == 4.0
    assert s["last_seen_at"] == "2026-10-13T12:00:00+00:00"
    ev = db.one("SELECT * FROM events WHERE type='SENSOR_MOVED'")
    assert ev["sensor_id"] == "0x01" and ev["message"] == "Frigo 1: da Gateway 1 a Cucina"
    assert moved == [(1, "0x01")]


def test_stale_cache_from_old_gateway_ignored(db):
    sts, moved = states2(), []
    _move(db, sts, moved)
    now = datetime(2026, 10, 13, 12, 5, tzinfo=timezone.utc)
    msg(db, sts, "0x01", {"temperature": 9.9, "last_seen": "2026-10-13T11:00:00Z"},
        gws=GW2, now=now, on_moved=lambda old, ieee: moved.append((old, ieee)))
    s = db.one("SELECT * FROM sensors")
    assert s["gateway_id"] == 2 and s["last_temp"] == 4.0
    assert moved == [(1, "0x01")]
    assert len(db.query("SELECT * FROM events WHERE type='SENSOR_MOVED'")) == 1


def test_back_at_written(db):
    sts = states2()
    t0 = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 13, 12, 7, tzinfo=timezone.utc)
    msg(db, sts, "bridge/state", b"online", gws=GW2, base="zigbee2mqtt_2", now=t0)
    msg(db, sts, "bridge/state", b"offline", gws=GW2, base="zigbee2mqtt_2", now=t0)
    assert sts[2].offline_since == t0
    msg(db, sts, "bridge/state", b"online", gws=GW2, base="zigbee2mqtt_2", now=t1)
    assert sts[2].offline_since is None
    row = db.one("SELECT back_at FROM gateway_state WHERE gateway_id=2")
    assert row["back_at"] == "2026-10-13T12:07:00+00:00"


def test_startup_online_keeps_offline_clock(db):
    sts = states2()
    msg(db, sts, "bridge/state", b"online", gws=GW2, base="zigbee2mqtt_2")
    assert db.one("SELECT back_at FROM gateway_state WHERE gateway_id=2") is None


def test_online_after_open_alarm_writes_back_at(db):
    # alarm opened before a restart: the first "online" is a real return
    db.execute("INSERT INTO gateway_state(gateway_id, offline_open) VALUES(2, 1)")
    sts = states2()
    msg(db, sts, "bridge/state", b"online", gws=GW2, base="zigbee2mqtt_2")
    assert db.one("SELECT back_at FROM gateway_state WHERE gateway_id=2")["back_at"]


def test_move_needs_real_last_seen(db):
    sts, moved = states2(), []
    add_sensor(db, ieee="0x01", last_temp=5.0, last_seen_at="2026-10-13T10:00:00+00:00",
               gateway_id=1)
    msg(db, sts, "0x01", {"temperature": 4.0}, gws=GW2, base="zigbee2mqtt_2",
        on_moved=lambda old, ieee: moved.append((old, ieee)))
    assert db.one("SELECT gateway_id FROM sensors")["gateway_id"] == 1 and moved == []


def test_devices_list_keeps_monitored_sensor_gateway(db):
    sts = states2()
    add_sensor(db, ieee="0x01", gateway_id=1)
    msg(db, sts, "bridge/devices", DEVICES)
    msg(db, sts, "bridge/devices", DEVICES, gws=GW2, base="zigbee2mqtt_2")
    rows = {r["ieee"]: r["gateway_id"] for r in db.query("SELECT * FROM discovered")}
    assert rows == {"0x01": 1, "0x02": 2}


def test_disconnect_marks_bridges_offline(db):
    from app.mqtt import MqttService
    m = MqttService(db, "localhost", gateways=GW2)
    m.states[1].online = True
    m._on_disconnect(None, None, None, "x")
    assert not m.states[1].online and m.states[1].offline_since is not None
    assert m.states[2].offline_since is None
