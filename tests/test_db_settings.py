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


def test_old_discovered_table_migrated(tmp_path):
    import sqlite3

    from app.db import Database
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE discovered(ieee TEXT PRIMARY KEY, friendly_name TEXT, model TEXT, "
                "first_seen TEXT, last_temp REAL)")
    con.execute("INSERT INTO discovered VALUES('0xaa','x','m','2026-10-01T00:00:00+00:00',4.0)")
    con.commit()
    con.close()
    db = Database(path)
    cols = [r["name"] for r in db.query("PRAGMA table_info(discovered)")]
    assert "last_seen" in cols and db.one("SELECT ieee FROM discovered")["ieee"] == "0xaa"
    db.close()
    Database(path).close()                    # second open: migration is idempotent
