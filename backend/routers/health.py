"""Health + service control endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api", tags=["health"])


def _uptime_s(started_at: datetime | None) -> int:
    if started_at is None:
        return 0
    return int((datetime.now(tz=timezone.utc) - started_at).total_seconds())


@router.get("/health")
async def health(request: Request):
    from backend.dependencies import get_db
    from backend.config import settings

    mqtt = getattr(request.app.state, "mqtt_client", None)
    scheduler = getattr(request.app.state, "scheduler", None)
    started_at = getattr(request.app.state, "started_at", None)
    sched_started = getattr(request.app.state, "scheduler_started_at", None)

    try:
        db = get_db()
        db_size = await db.get_size_mb()
        db_status = "ok"
    except Exception:
        db_size = 0.0
        db_status = "error"

    return {
        "system": {
            "started_at": started_at.isoformat() if started_at else None,
            "uptime_s":   _uptime_s(started_at),
            "version":    "2.0.0",
        },
        "mqtt": {
            "status":   mqtt.health_state if mqtt else "disconnected",
            "uptime_s": mqtt.uptime_s if mqtt else 0,
            "broker":   f"{settings.mqtt_host}:{settings.mqtt_port}",
        },
        "scheduler": {
            "status":   "running" if (scheduler and scheduler.running) else "stopped",
            "uptime_s": _uptime_s(sched_started),
            "next_run": _next_run_iso(scheduler),
        },
        "db": {
            "status":   db_status,
            "uptime_s": _uptime_s(started_at),
            "backend":  settings.database_backend,
            "size_mb":  round(db_size, 2),
        },
    }


def _next_run_iso(scheduler) -> str | None:
    if scheduler is None or not scheduler.running:
        return None
    jobs = scheduler.get_jobs()
    if not jobs:
        return None
    next_times = [j.next_run_time for j in jobs if j.next_run_time]
    if not next_times:
        return None
    return min(next_times).isoformat()


@router.post("/services/mqtt/{action}")
async def control_mqtt(action: str, request: Request):
    mqtt = getattr(request.app.state, "mqtt_client", None)
    if action == "stop":
        if mqtt:
            mqtt.stop()
        return {"status": "stopped"}
    elif action == "start":
        import asyncio
        from backend.services.mqtt_client import MQTTClient
        from backend.main import _on_mqtt_reading
        loop = asyncio.get_running_loop()
        new_mqtt = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
        new_mqtt.start(loop=loop)
        request.app.state.mqtt_client = new_mqtt
        return {"status": "started"}
    elif action == "restart":
        if mqtt:
            mqtt.stop()
        import asyncio
        from backend.services.mqtt_client import MQTTClient
        from backend.main import _on_mqtt_reading
        loop = asyncio.get_running_loop()
        new_mqtt = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
        new_mqtt.start(loop=loop)
        request.app.state.mqtt_client = new_mqtt
        return {"status": "restarted"}
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/services/scheduler/{action}")
async def control_scheduler(action: str, request: Request):
    scheduler = getattr(request.app.state, "scheduler", None)
    if action == "stop":
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        return {"status": "stopped"}
    elif action == "start":
        if scheduler and not scheduler.running:
            scheduler.start()
        return {"status": "started"}
    elif action == "restart":
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        if scheduler:
            scheduler.start()
        return {"status": "restarted"}
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/services/db/restart")
async def restart_db(request: Request):
    from backend.dependencies import close_db, get_db
    await close_db()
    get_db()  # Re-initialize
    return {"status": "restarted"}
