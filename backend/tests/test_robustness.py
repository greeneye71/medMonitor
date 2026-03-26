"""Robustness tests: endpoints must not crash even in degraded states."""
import os

os.environ["DATABASE_BACKEND"] = "tinyflux"
os.environ["SMTP_HOST"] = ""
os.environ["IMAP_HOST"] = ""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def test_client():
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


def test_health_no_crash_without_mqtt(test_client):
    """GET /api/health non crasha se mqtt_client è None."""
    r = test_client.get("/api/health")
    assert r.status_code == 200


def test_logs_empty_without_collector(test_client):
    """GET /api/logs restituisce [] se log_collector non è in app.state."""
    r = test_client.get("/api/logs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_zones_get(test_client):
    """GET /api/zones restituisce lista."""
    r = test_client.get("/api/zones")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sensor_discovered_empty(test_client):
    """GET /api/sensors/discovered restituisce [] con MQTT inattivo."""
    r = test_client.get("/api/sensors/discovered")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_archive_status_no_crash(test_client):
    """GET /api/archive/status non crasha se archive_log.json non esiste."""
    r = test_client.get("/api/archive/status")
    assert r.status_code == 200
    data = r.json()
    assert "last_run" in data
