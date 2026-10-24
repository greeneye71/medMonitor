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


def test_history_of_removed_sensor_not_swapped(client, app):
    db = app.state.db
    add_sensor(db, ieee="0x01", name="Frigo rimosso", active=0)
    add_sensor(db, ieee="0x02", name="Frigo attivo")
    r = client.get("/storico.csv?sensor=0x01")
    assert r.status_code == 200
    assert "Frigo_rimosso" in r.headers["content-disposition"]
    assert "Frigo rimosso" in client.get("/storico?sensor=0x01").text


def test_history_unknown_sensor_404(client, app):
    add_sensor(app.state.db)
    assert client.get("/storico.csv?sensor=0xdead").status_code == 404
    assert client.get("/storico?sensor=0xdead").status_code == 404


@pytest.mark.parametrize("bad", ["nan", "NaN", "inf", "-inf"])
def test_non_finite_thresholds_rejected(admin, app, bad):
    from app import settings
    db = app.state.db
    add_sensor(db)
    admin.post("/impostazioni/sensori/0x01/modifica",
               data={"name": "Frigo 1", "kind": "fridge", "min_c": bad, "max_c": "8"})
    s = db.one("SELECT min_c, max_c FROM sensors WHERE ieee='0x01'")
    assert (s["min_c"], s["max_c"]) == (2.0, 8.0)
    admin.post("/impostazioni/allarmi", data={"fridge_min": "2", "fridge_max": bad})
    assert settings.get(db, "presets")["fridge"]["max"] == 8


def test_banner_warns_when_email_not_configured(client, app):
    from app import settings
    from app.db import iso, utcnow
    db = app.state.db
    add_sensor(db, last_seen_at=iso(utcnow()))
    assert "Email di allarme non configurate" in client.get("/partials/cards").text
    settings.set(db, "smtp", {"host": "smtp.x.it"})
    assert "Email di allarme non configurate" in client.get("/partials/cards").text
    settings.set(db, "recipients", ["a@x.it"])
    r = client.get("/partials/cards").text
    assert "Email di allarme non configurate" not in r and "Tutto regolare" in r


def test_test_email_reports_refused_recipient(admin, app, monkeypatch):
    from aiosmtplib import SMTPResponse

    from app import notifier, settings
    db = app.state.db
    settings.set(db, "smtp", {"host": "smtp.x.it"})
    settings.set(db, "recipients", ["a@x.it", "b@x.it"])

    async def fake_send(msg, **kw):
        return {"b@x.it": SMTPResponse(550, "no such user")}, "OK"
    monkeypatch.setattr(notifier.aiosmtplib, "send", fake_send)
    r = admin.post("/impostazioni/email/prova")
    assert "Destinatari rifiutati" in r.text and "b@x.it (550 no such user)" in r.text


def test_added_sensor_keeps_real_last_seen(admin, app):
    from datetime import timedelta

    from app.db import iso, utcnow
    db = app.state.db
    old = iso(utcnow() - timedelta(hours=5))
    db.execute("INSERT INTO discovered(ieee, friendly_name, model, first_seen, last_temp, last_seen) "
               "VALUES('0xaa', '0xaa', 'SNZB-02LD', ?, 4.2, ?)", (old, old))
    admin.post("/impostazioni/sensori/aggiungi",
               data={"ieee": "0xaa", "name": "Frigo", "kind": "fridge", "min_c": "2", "max_c": "8"})
    assert db.one("SELECT last_seen_at FROM sensors WHERE ieee='0xaa'")["last_seen_at"] == old


def test_health_multi_gateway(client, app):
    from types import SimpleNamespace

    from app import __version__
    from app.gateways import Gateway
    from app.mqtt import BridgeState
    app.state.gateways = [Gateway(1, "Ambiente 1", "zigbee2mqtt", ""),
                          Gateway(2, "Ambulatorio", "zigbee2mqtt_2", "")]
    app.state.mqtt = SimpleNamespace(connected=True, stop=lambda: None, states={1: BridgeState(online=True),
                                                             2: BridgeState(online=False)})
    add_sensor(app.state.db)
    h = client.get("/health").json()
    assert h["version"] == __version__
    assert h["gateway_online"] is True        # gateway 2 is down but has no sensors
    assert h["gateways"] == [{"id": 1, "name": "Ambiente 1", "online": True, "sensors": 1},
                             {"id": 2, "name": "Ambulatorio", "online": False, "sensors": 0}]
    add_sensor(app.state.db, ieee="0x02", name="Frigo 2", gateway_id=2)
    assert client.get("/health").json()["gateway_online"] is False
