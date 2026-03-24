"""Sensors router — GET /api/sensors, PUT /api/sensors/{id}."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.models.reading import Sensor, SensorUpdate
from backend.paths import data_file
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

SENSORS_FILE = data_file("sensors.json")


def _load_sensors() -> dict[str, dict]:
    """Load sensors registry from file."""
    if SENSORS_FILE.exists():
        try:
            with open(SENSORS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _save_sensors(sensors: dict[str, dict]) -> None:
    """Persist sensors registry."""
    SENSORS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SENSORS_FILE, "w", encoding="utf-8") as f:
        json.dump(sensors, f, indent=2, ensure_ascii=False, default=str)


@router.get("/status")
async def get_sensors_status():
    """Return current alert level per sensor (OK / WARNING / CRITICAL).

    Looks at non-resolved alerts in the last 20 minutes.
    Sensors absent from the result are in OK state.
    Returns: {sensor_id: "WARNING" | "CRITICAL"}
    """
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=20)
    recent_alerts = await db.get_alerts(from_dt=cutoff)

    # Keep the worst active level per sensor
    PRIORITY = {"WARNING": 1, "CRITICAL": 2}
    status: dict[str, str] = {}
    for alert in recent_alerts:
        if alert.get("resolved"):
            continue
        sid = alert.get("sensor_id", "")
        level = alert.get("level", "WARNING")
        if sid not in status or PRIORITY.get(level, 0) > PRIORITY.get(status[sid], 0):
            status[sid] = level

    return status


@router.get("", response_model=list[Sensor])
async def get_sensors():
    """List all registered sensors."""
    sensors = _load_sensors()
    return [
        Sensor(sensor_id=sid, **data)
        for sid, data in sensors.items()
    ]


@router.put("/{sensor_id}", response_model=Sensor)
async def update_sensor(sensor_id: str, update: SensorUpdate):
    """Update sensor name, zone, or active status."""
    sensors = _load_sensors()

    if sensor_id not in sensors:
        sensors[sensor_id] = {"name": "", "zone": "fridge", "active": True}

    for field, value in update.model_dump(exclude_none=True).items():
        sensors[sensor_id][field] = value

    _save_sensors(sensors)
    logger.info("Sensor updated: %s", sensor_id)

    return Sensor(sensor_id=sensor_id, **sensors[sensor_id])
