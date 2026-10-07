import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import add_sensor

SETTINGS_PAGES = ["sensori", "email", "gateway", "allarmi", "archivio", "sicurezza"]


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, start_services=False, z2m_path=tmp_path / "configuration.yaml")


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(client):
    r = client.post("/login", data={"password": "admin", "next": "/impostazioni"},
                    follow_redirects=False)
    assert r.status_code == 303
    return client


@pytest.mark.parametrize("path", ["/", "/storico", "/eventi", "/login", "/health",
                                  "/partials/cards", "/storico.csv"])
def test_public_pages(client, app, path):
    add_sensor(app.state.db)
    assert client.get(path).status_code == 200


def test_settings_require_login(client):
    r = client.get("/impostazioni/sensori", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


def test_wrong_password(client):
    r = client.post("/login", data={"password": "nope"})
    assert r.status_code == 200
    assert 'class="error"' in r.text
    assert client.get("/impostazioni/sensori", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("tab", SETTINGS_PAGES)
def test_settings_pages_render(admin, app, tab):
    add_sensor(app.state.db)
    r = admin.get(f"/impostazioni/{tab}")
    assert r.status_code == 200
    assert 'aria-current="page"' in r.text


def test_invalid_thresholds_rejected(admin, app):
    add_sensor(app.state.db)
    r = admin.post("/impostazioni/sensori/0x01/modifica",
                   data={"name": "Frigo 1", "kind": "fridge", "min_c": "9", "max_c": "3"})
    assert r.status_code == 200
    assert "più bassa" in r.text
    s = app.state.db.one("SELECT min_c, max_c FROM sensors WHERE ieee='0x01'")
    assert (s["min_c"], s["max_c"]) == (2.0, 8.0)


def test_valid_thresholds_saved(admin, app):
    add_sensor(app.state.db)
    admin.post("/impostazioni/sensori/0x01/modifica",
               data={"name": "Frigo farmaci", "kind": "fridge", "min_c": "2,5", "max_c": "7"})
    s = app.state.db.one("SELECT name, min_c, max_c FROM sensors WHERE ieee='0x01'")
    assert (s["name"], s["min_c"], s["max_c"]) == ("Frigo farmaci", 2.5, 7.0)


def test_discovered_sensor_can_be_added(admin, app):
    app.state.db.execute("INSERT INTO discovered(ieee, friendly_name, model, first_seen, last_temp) "
                         "VALUES('0xaa', '0xaa', 'SNZB-02LD', '2026-10-08T08:00:00+00:00', 4.2)")
    r = admin.get("/impostazioni/sensori/rilevati")
    assert r.status_code == 200 and "0xaa" in r.text
    admin.post("/impostazioni/sensori/aggiungi",
               data={"ieee": "0xaa", "name": "Frigo vaccini", "kind": "fridge", "min_c": "2", "max_c": "8"})
    s = app.state.db.one("SELECT name, active FROM sensors WHERE ieee='0xaa'")
    assert (s["name"], s["active"]) == ("Frigo vaccini", 1)


def test_csv_export_non_ascii_name_and_formula(client, app):
    from datetime import timedelta

    from app.db import iso, utcnow
    db = app.state.db
    add_sensor(db, name="=Frigo “A” €")
    db.execute("INSERT INTO samples(sensor_id,ts,temp_c,battery) VALUES('0x01',?,4.2,80)",
               (iso(utcnow() - timedelta(minutes=10)),))
    r = client.get("/storico.csv?sensor=0x01")
    assert r.status_code == 200
    disp = r.headers["content-disposition"]
    assert disp.isascii() and "storico_Frigo_A_" in disp
    assert ";'=Frigo “A” €;4,2;80" in r.text


def test_edit_strips_control_chars(admin, app):
    add_sensor(app.state.db)
    admin.post("/impostazioni/sensori/0x01/modifica",
               data={"name": " Frigo\r\n\tuno\x00 ", "kind": "fridge", "min_c": "2", "max_c": "8"})
    assert app.state.db.one("SELECT name FROM sensors")["name"] == "Frigo uno"


def test_clear_smtp_password(admin, app):
    from app import settings
    db = app.state.db
    form = {"host": "smtp.x.it", "port": "587", "security": "starttls", "user": "u", "sender": "a@x.it"}
    admin.post("/impostazioni/email", data={**form, "password": "segreta"})
    assert settings.get(db, "smtp")["password"] == "segreta"
    admin.post("/impostazioni/email", data=form)                          # empty: keep
    assert settings.get(db, "smtp")["password"] == "segreta"
    admin.post("/impostazioni/email", data={**form, "clear_password": "1"})
    assert settings.get(db, "smtp")["password"] == ""


def test_gateway_page_with_malformed_yaml(admin, tmp_path):
    (tmp_path / "configuration.yaml").write_text("serial: [unclosed\n  : :", encoding="utf-8")
    assert admin.get("/impostazioni/gateway").status_code == 200
