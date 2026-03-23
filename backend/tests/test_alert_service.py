"""Tests for AlertService logic."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from backend.services.alert_service import AlertService


@pytest.mark.asyncio
async def test_warning_level(db_adapter, sample_reading):
    """Out of range 0-15 min should be WARNING."""
    # Write a reading out of range
    sample_reading["temperature"] = 35.0
    await db_adapter.write_reading(sample_reading)

    service = AlertService()

    with patch("backend.services.alert_service.get_db", return_value=db_adapter), \
         patch("backend.services.alert_service.send_alert_email", new_callable=AsyncMock) as mock_email:

        await service.check_alerts()

        # Should have created an alert
        alerts = await db_adapter.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["level"] == "WARNING"


@pytest.mark.asyncio
async def test_critical_level(db_adapter, sample_reading):
    """Out of range > 15 min should be CRITICAL."""
    sample_reading["temperature"] = 35.0
    await db_adapter.write_reading(sample_reading)

    service = AlertService()
    # Simulate sensor has been out of range for 20 minutes
    service._out_of_range_since[sample_reading["sensor_id"]] = (
        datetime.now(timezone.utc) - timedelta(minutes=20)
    )

    with patch("backend.services.alert_service.get_db", return_value=db_adapter), \
         patch("backend.services.alert_service.send_alert_email", new_callable=AsyncMock):

        await service.check_alerts()

        alerts = await db_adapter.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["level"] == "CRITICAL"


@pytest.mark.asyncio
async def test_cooldown(db_adapter, sample_reading):
    """Should not send duplicate emails within cooldown period."""
    sample_reading["temperature"] = 35.0
    await db_adapter.write_reading(sample_reading)

    service = AlertService()
    # Simulate email was sent 5 minutes ago
    service._last_email_sent[sample_reading["sensor_id"]] = (
        datetime.now(timezone.utc) - timedelta(minutes=5)
    )

    with patch("backend.services.alert_service.get_db", return_value=db_adapter), \
         patch("backend.services.alert_service.send_alert_email", new_callable=AsyncMock) as mock_email:

        await service.check_alerts()

        # Email should NOT be sent (cooldown 30 min, only 5 min elapsed)
        mock_email.assert_not_called()


@pytest.mark.asyncio
async def test_back_in_range_clears_tracking(db_adapter, sample_reading):
    """Returning to normal clears out-of-range tracking."""
    sample_reading["temperature"] = 4.0  # Normal
    await db_adapter.write_reading(sample_reading)

    service = AlertService()
    service._out_of_range_since[sample_reading["sensor_id"]] = datetime.now(timezone.utc)

    with patch("backend.services.alert_service.get_db", return_value=db_adapter), \
         patch("backend.services.alert_service.send_alert_email", new_callable=AsyncMock):

        await service.check_alerts()

        assert sample_reading["sensor_id"] not in service._out_of_range_since
