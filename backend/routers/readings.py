"""Readings router — GET /api/readings, GET /api/readings/latest."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.models.reading import Reading
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/readings", tags=["readings"])


@router.get("", response_model=list[Reading])
async def get_readings(
    zone: str | None = Query(None, description="Filter by zone (fridge/freezer)"),
    sensor_id: str | None = Query(None, description="Filter by sensor ID"),
    from_dt: datetime | None = Query(None, alias="from", description="Start datetime"),
    to_dt: datetime | None = Query(None, alias="to", description="End datetime"),
    limit: int = Query(1000, ge=1, le=10000),
):
    """Get temperature readings with optional filters."""
    try:
        db = get_db()
        return await db.get_readings(
            zone=zone, sensor_id=sensor_id, from_dt=from_dt, to_dt=to_dt, limit=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_readings failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=list[Reading])
async def get_latest():
    """Get the latest reading for each sensor."""
    try:
        db = get_db()
        return await db.get_latest()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_latest failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
