"""Readings router — GET /api/readings, GET /api/readings/latest."""

from datetime import datetime

from fastapi import APIRouter, Query

from backend.models.reading import Reading
from backend.dependencies import get_db

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
    db = get_db()
    return await db.get_readings(
        zone=zone, sensor_id=sensor_id, from_dt=from_dt, to_dt=to_dt, limit=limit,
    )


@router.get("/latest", response_model=list[Reading])
async def get_latest():
    """Get the latest reading for each sensor."""
    db = get_db()
    return await db.get_latest()
