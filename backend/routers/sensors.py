"""Sensors router — GET /api/sensors, PUT /api/sensors/{id}."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.models.reading import Sensor, SensorUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

SENSORS_FILE = Path("data/sensors.json")


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
