"""Tests for FastAPI endpoints using httpx AsyncClient."""

import os
os.environ["DATABASE_BACKEND"] = "tinyflux"
os.environ["TINYFLUX_PATH"] = "./data/test_api.db"
os.environ["SMTP_HOST"] = ""
os.environ["IMAP_HOST"] = ""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "medMonitor"


@pytest.mark.asyncio
async def test_get_config(client):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "thresholds" in data
    assert "email" in data


@pytest.mark.asyncio
async def test_get_thresholds(client):
    resp = await client.get("/api/thresholds")
    assert resp.status_code == 200
    data = resp.json()
    assert "defaults" in data


@pytest.mark.asyncio
async def test_get_readings_empty(client):
    resp = await client.get("/api/readings")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_readings_latest_empty(client):
    resp = await client.get("/api/readings/latest")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_alerts_empty(client):
    resp = await client.get("/api/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_sensors_empty(client):
    resp = await client.get("/api/sensors")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_demo_status(client):
    resp = await client.get("/api/demo/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data


@pytest.mark.asyncio
async def test_patch_config(client):
    resp = await client.patch("/api/config", json={"app_name": "TestApp"})
    assert resp.status_code == 200
    assert resp.json()["app_name"] == "TestApp"


@pytest.mark.asyncio
async def test_patch_config_empty(client):
    resp = await client.patch("/api/config", json={})
    assert resp.status_code == 400
