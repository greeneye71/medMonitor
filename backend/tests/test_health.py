"""Tests for /api/health endpoint."""

import os

os.environ["DATABASE_BACKEND"] = "tinyflux"
os.environ["SMTP_HOST"] = ""
os.environ["IMAP_HOST"] = ""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def test_client():
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


def test_health_returns_all_sections(test_client):
    """GET /api/health deve restituire system, mqtt, scheduler, db."""
    r = test_client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "system" in data
    assert "mqtt" in data
    assert "scheduler" in data
    assert "db" in data
    assert "version" in data["system"]
    assert "size_mb" in data["db"]
