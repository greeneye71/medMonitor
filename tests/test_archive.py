import csv
from datetime import datetime, timedelta, timezone

from app import archive
from app.db import iso
from tests.conftest import add_sensor

NOW = datetime(2026, 10, 8, 3, 0, tzinfo=timezone.utc)


def sample(db, ts, temp=4.0, ieee="0x01"):
    db.execute("INSERT INTO samples(sensor_id,ts,temp_c,battery) VALUES(?,?,?,?)",
               (ieee, iso(ts), temp, 80))


def test_old_samples_archived(db, tmp_path):
    add_sensor(db, name="Frigo Farmacia")
    sample(db, datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc), 4.5)
    sample(db, datetime(2026, 3, 31, 23, 30, tzinfo=timezone.utc), 5.0)   # 1 Apr local
    sample(db, NOW - timedelta(days=10), 6.0)
    n = archive.archive_old(db, tmp_path / "archive", NOW)
    assert n == 2
    assert db.one("SELECT COUNT(*) n FROM samples")["n"] == 1
    with open(tmp_path / "archive" / "2026-03.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == archive.HEADER
    assert rows[1][2] == "Frigo Farmacia" and rows[1][3] == "4.5"
    assert rows[1][0].startswith("2026-03-01T13:00")
    assert (tmp_path / "archive" / "2026-04.csv").exists()
    assert db.one("SELECT type FROM events")["type"] == "ARCHIVE"


def test_second_run_appends_without_header(db, tmp_path):
    add_sensor(db)
    sample(db, datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc))
    archive.archive_old(db, tmp_path, NOW)
    sample(db, datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc))
    archive.archive_old(db, tmp_path, NOW)
    with open(tmp_path / "2026-03.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3 and rows.count(archive.HEADER) == 1


def test_nothing_to_archive(db, tmp_path):
    assert archive.archive_old(db, tmp_path / "a", NOW) == 0
    assert archive.list_archives(tmp_path / "a") == []
    assert db.query("SELECT * FROM events") == []


def test_formula_names_escaped(db, tmp_path):
    add_sensor(db, name="=cmd|' /C calc'!A0")
    sample(db, datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc))
    archive.archive_old(db, tmp_path, NOW)
    with open(tmp_path / "2026-03.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1][2] == "'=cmd|' /C calc'!A0"
