"""Demo router — start/stop demo, status, reset data."""

import logging

from fastapi import APIRouter, HTTPException

from backend.dependencies import get_db
from backend.services.demo_generator import demo_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/start")
async def start_demo(payload: dict):
    """Start demo mode with a scenario and speed."""
    scenario = payload.get("scenario", "full_stress")
    speed = payload.get("speed", "10x")

    try:
        await demo_generator.start(scenario=scenario, speed=speed)
        return {
            "status": "ok",
            "message": f"Demo avviata: {scenario} a {speed}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_demo():
    """Stop demo mode."""
    await demo_generator.stop()
    return {"status": "ok", "message": "Demo fermata"}


@router.get("/status")
async def demo_status():
    """Get current demo status."""
    return demo_generator.status


@router.post("/reset")
async def reset_demo():
    """Delete all demo data (sensor_id starting with 0xDEMO)."""
    if demo_generator.is_active:
        await demo_generator.stop()

    db = get_db()
    count = await db.delete_demo_data()
    return {
        "status": "ok",
        "message": f"Cancellati {count} record demo",
        "deleted": count,
    }
