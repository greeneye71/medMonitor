"""Tests for threshold resolution — alert service uses sensor thresholds, not zone."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from backend.models.config_model import ThresholdsConfig, ZoneThresholds, SensorThreshold
from backend.services.alert_service import AlertService


def test_override_takes_priority():
    """resolve() returns sensor values when override=True."""
    config = ThresholdsConfig(
        defaults={"fridge": ZoneThresholds(min=0, max=30)},
        sensors={"0xSENSOR": SensorThreshold(zone="fridge", min=2.0, max=8.0, override=True)},
    )
    assert config.resolve("0xSENSOR") == (2.0, 8.0)


def test_no_override_uses_zone():
    """resolve() returns zone defaults when override=False."""
    config = ThresholdsConfig(
        defaults={"freezer": ZoneThresholds(min=-30, max=0)},
        sensors={"0xSENSOR": SensorThreshold(zone="freezer", min=-25.0, max=-5.0, override=False)},
    )
    assert config.resolve("0xSENSOR") == (-30.0, 0.0)


def test_multiple_sensors_different_overrides():
    """Each sensor resolves independently."""
    config = ThresholdsConfig(
        defaults={
            "fridge": ZoneThresholds(min=0, max=30),
            "freezer": ZoneThresholds(min=-30, max=0),
        },
        sensors={
            "0xA": SensorThreshold(zone="fridge", min=2, max=8, override=True),
            "0xB": SensorThreshold(zone="fridge", override=False),
            "0xC": SensorThreshold(zone="freezer", min=-25, max=-15, override=True),
        },
    )
    assert config.resolve("0xA") == (2.0, 8.0)
    assert config.resolve("0xB") == (0.0, 30.0)
    assert config.resolve("0xC") == (-25.0, -15.0)


@pytest.mark.asyncio
async def test_alert_uses_sensor_thresholds(db_adapter):
    """Alert service should use resolve() per sensor, not zone defaults."""
    # Sensor has tight thresholds: 2-8°C
    custom_thresholds = ThresholdsConfig(
        defaults={"fridge": ZoneThresholds(min=0, max=30)},
        sensors={
            "0xTIGHT": SensorThreshold(zone="fridge", min=2.0, max=8.0, override=True),
        },
    )

    # 10°C is within zone default (0-30) but outside sensor threshold (2-8)
    reading = {
        "zone": "fridge",
        "sensor_id": "0xTIGHT",
        "temperature": 10.0,
        "humidity": None,
        "battery": None,
        "timestamp": datetime.now(timezone.utc),
    }
    await db_adapter.write_reading(reading)

    service = AlertService()

    mock_config = type("MockConfig", (), {
        "thresholds": custom_thresholds,
        "alert_cooldown_minutes": 30,
    })()

    with patch("backend.services.alert_service.get_db", return_value=db_adapter), \
         patch("backend.services.alert_service.config_service") as mock_cs, \
         patch("backend.services.alert_service.send_alert_email", new_callable=AsyncMock):

        mock_cs.get_config.return_value = mock_config
        await service.check_alerts()

        alerts = await db_adapter.get_alerts()
        # Should trigger alert because 10°C > 8°C (sensor max)
        assert len(alerts) == 1
        assert alerts[0]["sensor_id"] == "0xTIGHT"
