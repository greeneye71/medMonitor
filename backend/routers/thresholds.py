"""Thresholds router — per-sensor threshold management."""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.config_model import (
    ThresholdsConfig,
    ThresholdDefaultsPatch,
    SensorThresholdPatch,
    ZoneThresholds,
)
from backend.services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/thresholds", tags=["thresholds"])


@router.get("")
async def get_thresholds():
    """Return thresholds with effective_min/max for each sensor."""
    try:
        thresholds = config_service.get_thresholds()

        # Build response with effective values
        sensors_effective = {}
        for sensor_id, sensor in thresholds.sensors.items():
            eff_min, eff_max = thresholds.resolve(sensor_id)
            sensors_effective[sensor_id] = {
                **sensor.model_dump(),
                "effective_min": eff_min,
                "effective_max": eff_max,
            }

        return {
            "defaults": thresholds.defaults,
            "sensors": sensors_effective,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_thresholds failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/defaults")
async def patch_defaults(patch: ThresholdDefaultsPatch):
    """Update zone default thresholds."""
    try:
        if not patch.zones:
            raise HTTPException(status_code=400, detail="No zone defaults to update")

        thresholds = config_service.update_threshold_defaults(patch.zones)
        return {"status": "ok", "defaults": thresholds.defaults}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("patch_defaults failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sensor/{sensor_id}")
async def patch_sensor(sensor_id: str, patch: SensorThresholdPatch):
    """Update individual sensor thresholds."""
    try:
        updates = patch.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        thresholds = config_service.update_sensor_threshold(sensor_id, updates)
        eff_min, eff_max = thresholds.resolve(sensor_id)

        sensor = thresholds.sensors[sensor_id]
        return {
            "status": "ok",
            "sensor_id": sensor_id,
            **sensor.model_dump(),
            "effective_min": eff_min,
            "effective_max": eff_max,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("patch_sensor failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sensor/{sensor_id}")
async def delete_sensor_threshold(sensor_id: str):
    """Remove sensor-specific thresholds (revert to zone defaults)."""
    try:
        thresholds = config_service.delete_sensor_threshold(sensor_id)
        return {
            "status": "ok",
            "message": f"Soglie individuali rimosse per {sensor_id}",
            "defaults": thresholds.defaults,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_sensor_threshold failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
