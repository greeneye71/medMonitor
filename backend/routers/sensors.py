"""Sensors router — GET /api/sensors, PUT /api/sensors/{id}, plus discovery endpoints."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.models.reading import Sensor, SensorUpdate
from backend.paths import data_file
from backend.dependencies import get_db
from backend.services.config_service import config_service

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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sensors_status failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[Sensor])
async def get_sensors():
    """List all registered sensors."""
    try:
        sensors = _load_sensors()
        return [
            Sensor(sensor_id=sid, **data)
            for sid, data in sensors.items()
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_sensors failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovered")
async def get_discovered(request: Request):
    """List sensors detected via MQTT not yet in sensors.json."""
    try:
        mqtt = getattr(request.app.state, "mqtt_client", None)
        discovered = mqtt.discovered_sensors if mqtt else set()

        sensors_file = data_file("sensors.json")
        configured = set()
        if sensors_file.exists():
            configured = set(json.loads(sensors_file.read_text(encoding="utf-8")).keys())

        # Only those not yet configured
        new_ids = discovered - configured
        return [{"sensor_id": sid, "first_seen": None, "last_seen": None, "last_temp": None}
                for sid in sorted(new_ids)]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_discovered failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class SensorAcceptBody(BaseModel):
    name: str
    zone: str
    min: float | None = None
    max: float | None = None


@router.post("/{sensor_id}/accept")
async def accept_sensor(sensor_id: str, body: SensorAcceptBody):
    """Accept a discovered sensor: register it and optionally set thresholds."""
    try:
        sensors_file = data_file("sensors.json")
        sensors = {}
        if sensors_file.exists():
            sensors = json.loads(sensors_file.read_text(encoding="utf-8"))
        sensors[sensor_id] = {"name": body.name, "zone": body.zone, "active": True}
        sensors_file.parent.mkdir(parents=True, exist_ok=True)
        sensors_file.write_text(json.dumps(sensors, indent=2), encoding="utf-8")

        if body.min is not None and body.max is not None:
            config_service.update_sensor_threshold(sensor_id, {
                "name": body.name,
                "zone": body.zone,
                "min": body.min,
                "max": body.max,
                "override": True,
            })

        return {"accepted": sensor_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("accept_sensor failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{sensor_id}")
async def delete_sensor(sensor_id: str):
    """Remove sensor from sensors.json and thresholds (data preserved in DB)."""
    try:
        sensors_file = data_file("sensors.json")
        if sensors_file.exists():
            sensors = json.loads(sensors_file.read_text(encoding="utf-8"))
            sensors.pop(sensor_id, None)
            sensors_file.write_text(json.dumps(sensors, indent=2), encoding="utf-8")
        config_service.delete_sensor_threshold(sensor_id)
        return {"deleted": sensor_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_sensor failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{sensor_id}", response_model=Sensor)
async def update_sensor(sensor_id: str, update: SensorUpdate):
    """Update sensor name, zone, or active status."""
    try:
        sensors = _load_sensors()

        if sensor_id not in sensors:
            sensors[sensor_id] = {"name": "", "zone": "fridge", "active": True}

        for field, value in update.model_dump(exclude_none=True).items():
            sensors[sensor_id][field] = value

        _save_sensors(sensors)
        logger.info("Sensor updated: %s", sensor_id)

        return Sensor(sensor_id=sensor_id, **sensors[sensor_id])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_sensor failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
