from app import settings
from app.db import parse, iso, utcnow


def test_schema_tables(db):
    names = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sensors", "samples", "events", "alert_state", "outbox", "discovered", "settings"} <= names


def test_settings_defaults(db):
    assert settings.get(db, "alarm") == {"consecutive_samples": 2, "offline_minutes": 120,
                                         "battery_percent": 20}
    assert settings.get(db, "recipients") == []


def test_settings_roundtrip_and_merge(db):
    settings.set(db, "alarm", {"consecutive_samples": 3})
    a = settings.get(db, "alarm")
    assert a["consecutive_samples"] == 3 and a["offline_minutes"] == 120
    settings.set(db, "recipients", ["a@b.it"])
    assert settings.get(db, "recipients") == ["a@b.it"]


def test_iso_roundtrip():
    now = utcnow()
    assert parse(iso(now)) == now
