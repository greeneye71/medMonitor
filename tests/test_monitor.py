from datetime import datetime, timedelta, timezone

from app import monitor
from app.db import Database, iso
from tests.conftest import add_sensor

T0 = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
STEP = timedelta(minutes=10)


def cycle(db, i, temp=None, battery=None, seen=True):
    """Simulate MQTT updates just before tick i, then run the sampling cycle."""
    now = T0 + i * STEP
    sets, params = [], []
    if temp is not None:
        sets.append("last_temp=?")
        params.append(temp)
    if battery is not None:
        sets.append("last_battery=?")
        params.append(battery)
    if seen:
        sets.append("last_seen_at=?")
        params.append(iso(now - timedelta(minutes=1)))
    if sets:
        db.execute(f"UPDATE sensors SET {','.join(sets)} WHERE ieee='0x01'", params)
    monitor.run_cycle(db, now)
    return now


def events(db):
    return [e["type"] for e in db.query("SELECT type FROM events ORDER BY id")]


def outbox(db):
    return [o["subject"] for o in db.query("SELECT subject FROM outbox ORDER BY id")]


def setup_sensor(db):
    add_sensor(db, last_seen_at=iso(T0))


def test_two_out_of_range_open_once(db):
    setup_sensor(db)
    cycle(db, 0, temp=9.4)
    assert events(db) == []
    cycle(db, 1, temp=9.6)
    assert events(db) == ["TEMP_OPEN"]
    assert len(outbox(db)) == 1 and "ALLARME TEMPERATURA" in outbox(db)[0]
    cycle(db, 2, temp=10.0)
    assert len(outbox(db)) == 1
    assert db.one("SELECT COUNT(*) n FROM samples")["n"] == 3


def test_back_in_range_closes(db):
    setup_sensor(db)
    cycle(db, 0, temp=1.0)
    cycle(db, 1, temp=1.0)
    cycle(db, 2, temp=4.0)
    assert events(db) == ["TEMP_OPEN", "TEMP_CLOSE"]
    assert "RIENTRATA" in outbox(db)[1]
    st = db.one("SELECT * FROM alert_state")
    assert st["consecutive_out"] == 0 and st["temp_open"] == 0


def test_in_range_resets_counter(db):
    setup_sensor(db)
    cycle(db, 0, temp=9)
    cycle(db, 1, temp=5)
    cycle(db, 2, temp=9)
    assert events(db) == []


def test_offline_opens_and_keeps_counter(db):
    setup_sensor(db)
    cycle(db, 0, temp=9)                      # first out-of-range sample
    cycle(db, 13, seen=False)                 # next tick: no messages for > 120 min
    assert events(db) == ["OFFLINE_OPEN"]
    assert "NON RISPONDE" in outbox(db)[0]
    st = db.one("SELECT * FROM alert_state")
    assert st["consecutive_out"] == 1 and st["temp_open"] == 0
    assert db.one("SELECT COUNT(*) n FROM samples")["n"] == 1
    cycle(db, 14, temp=5)
    assert events(db) == ["OFFLINE_OPEN", "OFFLINE_CLOSE"]
    assert "DI NUOVO ONLINE" in outbox(db)[1]


def test_battery_hysteresis(db):
    setup_sensor(db)
    cycle(db, 0, battery=15)
    assert events(db) == ["BATTERY_OPEN"] and len(outbox(db)) == 1
    cycle(db, 1, battery=22)
    assert events(db) == ["BATTERY_OPEN"]
    cycle(db, 2, battery=26)
    assert events(db) == ["BATTERY_OPEN", "BATTERY_CLOSE"]
    assert len(outbox(db)) == 1


def test_mute_suppresses_then_requeues(db):
    setup_sensor(db)
    db.execute("UPDATE sensors SET muted_until=?", (iso(T0 + 3 * STEP + timedelta(minutes=5)),))
    cycle(db, 0, temp=12)
    cycle(db, 1, temp=12)
    assert events(db) == ["TEMP_OPEN"] and outbox(db) == []
    cycle(db, 2, temp=12)
    cycle(db, 3, temp=12)
    assert outbox(db) == []
    cycle(db, 4, temp=12)                     # mute expired, alarm still open
    assert len(outbox(db)) == 1 and "ALLARME" in outbox(db)[0]
    cycle(db, 5, temp=12)
    assert len(outbox(db)) == 1


def test_mute_expired_after_close_sends_nothing(db):
    setup_sensor(db)
    db.execute("UPDATE sensors SET muted_until=?", (iso(T0 + 3 * STEP + timedelta(minutes=5)),))
    cycle(db, 0, temp=12)
    cycle(db, 1, temp=12)
    cycle(db, 2, temp=5)
    cycle(db, 4, temp=5)
    assert outbox(db) == []


def test_inactive_sensor_ignored(db):
    add_sensor(db, last_seen_at=None, active=0)
    monitor.run_cycle(db, T0)
    assert events(db) == [] and outbox(db) == []


def test_state_survives_restart(tmp_path):
    db = Database(tmp_path / "r.db")
    add_sensor(db, last_seen_at=iso(T0))
    cycle(db, 0, temp=9)
    db.close()
    db = Database(tmp_path / "r.db")
    cycle(db, 1, temp=9)
    assert events(db) == ["TEMP_OPEN"]
    db.close()
