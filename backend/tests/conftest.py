"""Test fixtures — in-memory TinyFlux adapter, mock MQTT, mock SMTP."""

import os
import tempfile

import pytest
import pytest_asyncio

# Set env before importing app modules
os.environ["DATABASE_BACKEND"] = "tinyflux"
os.environ["SMTP_HOST"] = ""
os.environ["IMAP_HOST"] = ""


@pytest.fixture
def tinyflux_path(tmp_path):
    """Provide a temporary TinyFlux database path."""
    return str(tmp_path / "test_temperature.db")


@pytest_asyncio.fixture
async def db_adapter(tinyflux_path):
    """Provide a TinyFlux adapter for testing."""
    from backend.database.tinyflux_adapter import TinyFluxAdapter
    adapter = TinyFluxAdapter(tinyflux_path)
    yield adapter
    await adapter.close()


@pytest.fixture
def sample_reading():
    """A sample temperature reading."""
    from datetime import datetime, timezone
    return {
        "zone": "fridge",
        "sensor_id": "0xTEST_FRIDGE",
        "temperature": 4.2,
        "humidity": 55.0,
        "battery": 85,
        "timestamp": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_alert():
    """A sample alert record."""
    from datetime import datetime, timezone
    return {
        "zone": "fridge",
        "sensor_id": "0xTEST_FRIDGE",
        "temperature": 35.0,
        "level": "CRITICAL",
        "threshold_min": 0.0,
        "threshold_max": 30.0,
        "message": "Test alert",
        "timestamp": datetime.now(timezone.utc),
    }


@pytest.fixture
def demo_reading():
    """A demo temperature reading."""
    from datetime import datetime, timezone
    return {
        "zone": "fridge",
        "sensor_id": "0xDEMO_FRIDGE",
        "temperature": 5.0,
        "humidity": 50.0,
        "battery": 100,
        "timestamp": datetime.now(timezone.utc),
    }
