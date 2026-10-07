import pytest

from app.db import Database


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "t.db")
    yield d
    d.close()


def add_sensor(db, ieee="0x01", name="Frigo 1", kind="fridge", min_c=2.0, max_c=8.0,
               last_temp=5.0, last_battery=90, last_seen_at=None, active=1):
    db.execute("INSERT INTO sensors(ieee,name,kind,min_c,max_c,active,last_temp,last_battery,"
               "last_seen_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
               (ieee, name, kind, min_c, max_c, active, last_temp, last_battery, last_seen_at,
                last_seen_at))
