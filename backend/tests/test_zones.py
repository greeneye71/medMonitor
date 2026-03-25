"""Tests for /api/zones endpoints."""

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


def test_get_zones(test_client):
    r = test_client.get("/api/zones")
    assert r.status_code == 200
    zones = r.json()
    assert isinstance(zones, list)
    # Default config ha fridge + freezer
    names = [z["name"] for z in zones]
    assert "fridge" in names
    assert "freezer" in names


def test_post_zone(test_client):
    r = test_client.post("/api/zones", json={
        "name": "cold_room",
        "color": "#a855f7",
        "threshold_min": 2.0,
        "threshold_max": 8.0,
    })
    assert r.status_code in (200, 201)
    r2 = test_client.get("/api/zones")
    names = [z["name"] for z in r2.json()]
    assert "cold_room" in names


def test_delete_zone_no_sensors(test_client):
    test_client.post("/api/zones", json={
        "name": "temp_zone", "color": "#111",
        "threshold_min": 0.0, "threshold_max": 10.0,
    })
    r = test_client.delete("/api/zones/temp_zone")
    assert r.status_code == 200
