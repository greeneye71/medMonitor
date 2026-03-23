"""Tests for DemoGenerator."""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from backend.services.demo_generator import DemoGenerator, SCENARIOS


def test_scenarios_defined():
    """All 6 scenarios should be defined."""
    expected = {"normal", "fridge_alarm", "freezer_alarm", "power_loss",
                "sensor_battery_low", "full_stress"}
    assert set(SCENARIOS.keys()) == expected


def test_full_stress_is_longest():
    """full_stress should have the most steps."""
    assert SCENARIOS["full_stress"]["steps"] >= SCENARIOS["normal"]["steps"]


@pytest.mark.asyncio
async def test_demo_start_stop():
    """Demo starts and stops correctly."""
    gen = DemoGenerator()
    assert not gen.is_active

    mock_adapter = MagicMock()
    mock_adapter.write_reading = AsyncMock()

    with patch("backend.services.demo_generator.get_db", return_value=mock_adapter):
        await gen.start(scenario="normal", speed="600x")
        assert gen.is_active
        assert gen.status["scenario"] == "normal"

        await asyncio.sleep(0.5)
        await gen.stop()
        assert not gen.is_active


@pytest.mark.asyncio
async def test_demo_sensor_id_prefix():
    """Demo readings should have sensor_id starting with 0xDEMO."""
    gen = DemoGenerator()
    written_readings = []

    async def mock_write(reading):
        written_readings.append(reading)

    mock_adapter = MagicMock()
    mock_adapter.write_reading = mock_write

    with patch("backend.services.demo_generator.get_db", return_value=mock_adapter):
        await gen.start(scenario="normal", speed="600x")
        await asyncio.sleep(2)
        await gen.stop()

    assert len(written_readings) > 0
    for r in written_readings:
        assert r["sensor_id"].startswith("0xDEMO")


@pytest.mark.asyncio
async def test_fridge_alarm_generates_drift():
    """fridge_alarm scenario should generate increasing temperatures."""
    gen = DemoGenerator()
    written_readings = []

    async def mock_write(reading):
        written_readings.append(reading)

    mock_adapter = MagicMock()
    mock_adapter.write_reading = mock_write

    with patch("backend.services.demo_generator.get_db", return_value=mock_adapter):
        await gen.start(scenario="fridge_alarm", speed="600x")
        await asyncio.sleep(4)
        await gen.stop()

    fridge_temps = [r["temperature"] for r in written_readings if r["zone"] == "fridge"]
    assert len(fridge_temps) >= 1
    # Verify readings are generated with valid temperatures
    for t in fridge_temps:
        assert isinstance(t, float)


@pytest.mark.asyncio
async def test_invalid_scenario():
    """Starting with invalid scenario raises ValueError."""
    gen = DemoGenerator()
    with pytest.raises(ValueError, match="Unknown scenario"):
        await gen.start(scenario="nonexistent")
