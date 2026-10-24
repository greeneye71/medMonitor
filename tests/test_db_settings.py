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


V20_SCHEMA = """
CREATE TABLE sensors(ieee TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT, min_c REAL NOT NULL,
    max_c REAL NOT NULL, active INTEGER DEFAULT 1, muted_until TEXT, last_temp REAL,
    last_battery INTEGER, last_seen_at TEXT, created_at TEXT);
CREATE TABLE discovered(ieee TEXT PRIMARY KEY, friendly_name TEXT, model TEXT, first_seen TEXT,
    last_temp REAL, last_seen TEXT);
INSERT INTO sensors(ieee,name,kind,min_c,max_c) VALUES('0x01','Frigo','fridge',2,8);
INSERT INTO discovered(ieee,friendly_name) VALUES('0x02','nuovo');
"""


def test_migrate_adds_gateway_id(tmp_path):
    import sqlite3
    from app.db import Database
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript(V20_SCHEMA)
    con.close()
    db = Database(path)
    assert db.one("SELECT gateway_id FROM sensors")["gateway_id"] == 1
    assert db.one("SELECT gateway_id FROM discovered")["gateway_id"] == 1
    db.execute("INSERT INTO gateway_state(gateway_id) VALUES(2)")
    g = db.one("SELECT * FROM gateway_state")
    assert g["offline_open"] == 0 and g["email_sent"] == 0 and g["back_at"] is None


def test_migrate_idempotent(tmp_path):
    from app.db import Database
    path = tmp_path / "t.db"
    Database(path).execute("INSERT INTO sensors(ieee,name,kind,min_c,max_c,gateway_id) "
                           "VALUES('0x01','F','fridge',2,8,3)")
    db = Database(path)
    assert db.one("SELECT gateway_id FROM sensors")["gateway_id"] == 3
