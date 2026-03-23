"""Tests for DatabaseAdapter — TinyFlux implementation."""

import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_write_and_read_reading(db_adapter, sample_reading):
    await db_adapter.write_reading(sample_reading)
    readings = await db_adapter.get_readings()
    assert len(readings) == 1
    assert readings[0]["temperature"] == 4.2
    assert readings[0]["zone"] == "fridge"
    assert readings[0]["sensor_id"] == "0xTEST_FRIDGE"


@pytest.mark.asyncio
async def test_get_readings_filter_zone(db_adapter, sample_reading):
    await db_adapter.write_reading(sample_reading)

    freezer_reading = {**sample_reading, "zone": "freezer", "sensor_id": "0xTEST_FREEZER", "temperature": -20.0}
    await db_adapter.write_reading(freezer_reading)

    fridge_only = await db_adapter.get_readings(zone="fridge")
    assert len(fridge_only) == 1
    assert fridge_only[0]["zone"] == "fridge"


@pytest.mark.asyncio
async def test_get_readings_filter_time(db_adapter):
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    old_reading = {
        "zone": "fridge", "sensor_id": "0xTEST", "temperature": 3.0,
        "humidity": None, "battery": None, "timestamp": now - timedelta(hours=48),
    }
    new_reading = {
        "zone": "fridge", "sensor_id": "0xTEST", "temperature": 5.0,
        "humidity": None, "battery": None, "timestamp": now,
    }
    await db_adapter.write_reading(old_reading)
    await db_adapter.write_reading(new_reading)

    recent = await db_adapter.get_readings(from_dt=now - timedelta(hours=1))
    assert len(recent) == 1
    assert recent[0]["temperature"] == 5.0


@pytest.mark.asyncio
async def test_get_latest(db_adapter):
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    readings = [
        {"zone": "fridge", "sensor_id": "0xA", "temperature": 3.0, "humidity": None, "battery": None, "timestamp": now - timedelta(minutes=10)},
        {"zone": "fridge", "sensor_id": "0xA", "temperature": 5.0, "humidity": None, "battery": None, "timestamp": now},
        {"zone": "freezer", "sensor_id": "0xB", "temperature": -18.0, "humidity": None, "battery": None, "timestamp": now},
    ]
    for r in readings:
        await db_adapter.write_reading(r)

    latest = await db_adapter.get_latest()
    assert len(latest) == 2

    temps = {r["sensor_id"]: r["temperature"] for r in latest}
    assert temps["0xA"] == 5.0
    assert temps["0xB"] == -18.0


@pytest.mark.asyncio
async def test_write_and_read_alert(db_adapter, sample_alert):
    await db_adapter.write_alert(sample_alert)
    alerts = await db_adapter.get_alerts()
    assert len(alerts) == 1
    assert alerts[0]["level"] == "CRITICAL"
    assert alerts[0]["temperature"] == 35.0


@pytest.mark.asyncio
async def test_get_alerts_filter_level(db_adapter, sample_alert):
    await db_adapter.write_alert(sample_alert)

    warning_alert = {**sample_alert, "level": "WARNING", "temperature": 31.0}
    await db_adapter.write_alert(warning_alert)

    critical_only = await db_adapter.get_alerts(level="CRITICAL")
    assert len(critical_only) == 1


@pytest.mark.asyncio
async def test_delete_demo_data(db_adapter, sample_reading, demo_reading):
    await db_adapter.write_reading(sample_reading)
    await db_adapter.write_reading(demo_reading)

    all_readings = await db_adapter.get_readings()
    assert len(all_readings) == 2

    deleted = await db_adapter.delete_demo_data()
    assert deleted >= 1

    remaining = await db_adapter.get_readings()
    assert len(remaining) == 1
    assert remaining[0]["sensor_id"] == "0xTEST_FRIDGE"


@pytest.mark.asyncio
async def test_get_readings_limit(db_adapter):
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    for i in range(10):
        await db_adapter.write_reading({
            "zone": "fridge", "sensor_id": "0xTEST", "temperature": float(i),
            "humidity": None, "battery": None, "timestamp": now + timedelta(minutes=i),
        })

    limited = await db_adapter.get_readings(limit=3)
    assert len(limited) == 3
