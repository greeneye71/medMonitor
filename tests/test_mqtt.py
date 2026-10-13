import json

from app.mqtt import BridgeState, handle_message
from tests.conftest import add_sensor

DEVICES = [
    {"ieee_address": "0x00", "friendly_name": "Coordinator", "type": "Coordinator"},
    {"ieee_address": "0x01", "friendly_name": "frigo_farmacia", "type": "EndDevice",
     "definition": {"model": "SNZB-02LD"}},
    {"ieee_address": "0x02", "friendly_name": "nuovo", "type": "EndDevice",
     "definition": {"model": "SNZB-02LD"}},
]


def msg(db, state, topic, data):
    raw = data if isinstance(data, bytes) else json.dumps(data).encode()
    handle_message(db, state, "zigbee2mqtt/" + topic, raw)


def test_devices_map_skips_coordinator(db):
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    assert st.devices == {"frigo_farmacia": "0x01", "nuovo": "0x02"}
    assert st.models["0x01"] == "SNZB-02LD"


def test_registered_sensor_updates_last(db):
    add_sensor(db, ieee="0x01", last_temp=None, last_battery=None)
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    msg(db, st, "frigo_farmacia", {"temperature": 4.3, "battery": 87, "linkquality": 100})
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 4.3 and s["last_battery"] == 87 and s["last_seen_at"]
    msg(db, st, "frigo_farmacia", {"temperature": 4.5})       # battery missing: keep old
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 4.5 and s["last_battery"] == 87


def test_unregistered_goes_to_discovered(db):
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    msg(db, st, "nuovo", {"temperature": 6.1, "battery": 100})
    d = db.one("SELECT * FROM discovered WHERE ieee='0x02'")
    assert d["last_temp"] == 6.1 and d["model"] == "SNZB-02LD"


def test_bad_payloads_ignored(db):
    add_sensor(db, ieee="0x01", last_temp=5.0, last_seen_at=None)
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    msg(db, st, "frigo_farmacia", b"not json{")
    msg(db, st, "frigo_farmacia", {"battery": 50})
    msg(db, st, "frigo_farmacia", {"temperature": "hot"})
    msg(db, st, "frigo_farmacia", [1, 2])
    msg(db, st, "bridge/devices", b"garbage")
    msg(db, st, "sconosciuto", {"temperature": 3})
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 5.0 and s["last_seen_at"] is None
    assert st.devices["frigo_farmacia"] == "0x01"


def test_bridge_state_and_info(db):
    st = BridgeState()
    msg(db, st, "bridge/state", {"state": "online"})
    assert st.online
    msg(db, st, "bridge/state", b"offline")
    assert not st.online
    msg(db, st, "bridge/state", b"online")
    assert st.online
    msg(db, st, "bridge/info", {"version": "2.1.0"})
    assert st.version == "2.1.0"


def test_ieee_friendly_name_fallback(db):
    add_sensor(db, ieee="0xabc", last_temp=None)
    st = BridgeState()
    msg(db, st, "0xabc", {"temperature": -18.2})
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == -18.2


def test_non_finite_values_ignored(db):
    add_sensor(db, ieee="0x01", last_temp=5.0, last_battery=90)
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    msg(db, st, "frigo_farmacia", b'{"temperature": NaN}')
    msg(db, st, "frigo_farmacia", b'{"temperature": Infinity}')
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == 5.0
    msg(db, st, "frigo_farmacia", b'{"temperature": 4.0, "battery": NaN}')
    s = db.one("SELECT * FROM sensors")
    assert s["last_temp"] == 4.0 and s["last_battery"] == 90


def test_inactive_sensor_goes_to_discovered(db):
    add_sensor(db, ieee="0x01", last_temp=5.0, active=0)
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    msg(db, st, "frigo_farmacia", {"temperature": 3.3})
    assert db.one("SELECT last_temp FROM sensors")["last_temp"] == 5.0
    assert db.one("SELECT last_temp FROM discovered WHERE ieee='0x01'")["last_temp"] == 3.3


def test_discovered_records_last_seen(db):
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    msg(db, st, "nuovo", {"temperature": 6.1})
    d = db.one("SELECT first_seen, last_seen FROM discovered WHERE ieee='0x02'")
    assert d["last_seen"] is not None and d["last_seen"] >= d["first_seen"]


def test_cached_state_keeps_real_last_seen(db):
    # z2m republishes its state cache at startup: the payload's last_seen is the real
    # time the sensor spoke, not the time we received the message.
    from datetime import datetime, timezone
    add_sensor(db, ieee="0x01", last_temp=None, last_battery=None, last_seen_at=None)
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    now = datetime(2026, 10, 13, 12, 25, tzinfo=timezone.utc)
    handle_message(db, st, "zigbee2mqtt/frigo_farmacia", json.dumps(
        {"temperature": 24.9, "last_seen": "2026-10-09T09:41:12.356Z"}).encode(), now=now)
    s = db.one("SELECT * FROM sensors")
    assert s["last_seen_at"] == "2026-10-09T09:41:12+00:00"
    d = db.one("SELECT last_seen FROM discovered WHERE ieee='0x01'")
    assert d is None or d["last_seen"] == "2026-10-09T09:41:12+00:00"


def test_last_seen_epoch_future_and_garbage(db):
    from datetime import datetime, timezone
    add_sensor(db, ieee="0x01", last_temp=None, last_battery=None, last_seen_at=None)
    st = BridgeState()
    msg(db, st, "bridge/devices", DEVICES)
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)

    def seen(last_seen):
        handle_message(db, st, "zigbee2mqtt/frigo_farmacia", json.dumps(
            {"temperature": 4.0, "last_seen": last_seen}).encode(), now=now)
        return db.one("SELECT last_seen_at FROM sensors")["last_seen_at"]

    assert seen(int(datetime(2026, 10, 13, 11, 0, tzinfo=timezone.utc).timestamp() * 1000)) \
        == "2026-10-13T11:00:00+00:00"                          # epoch ms
    assert seen("2026-10-13T13:00:00Z") == "2026-10-13T12:00:00+00:00"   # future: clamp to now
    assert seen("garbage") == "2026-10-13T12:00:00+00:00"                # unparseable: now
    assert seen(True) == "2026-10-13T12:00:00+00:00"
