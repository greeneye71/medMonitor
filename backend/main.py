"""medMonitor — FastAPI backend entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.dependencies import close_db, get_db
from backend.routers import config as config_router
from backend.routers import thresholds as thresholds_router
from backend.routers import readings as readings_router
from backend.routers import sensors as sensors_router
from backend.routers import alerts as alerts_router
from backend.routers import demo as demo_router
from backend.services.alert_service import alert_service
from backend.services.imap_service import imap_service
from backend.services.mqtt_client import MQTTClient
from backend.services.config_service import config_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Module-level references so health_check can inspect them
_mqtt_client: MQTTClient | None = None
_scheduler: AsyncIOScheduler | None = None


async def _on_mqtt_reading(reading: dict) -> None:
    """Async callback invoked (via run_coroutine_threadsafe) for each MQTT reading."""
    try:
        db = get_db()
        await db.write_reading(reading)
    except Exception as e:
        logger.error("Failed to write MQTT reading: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mqtt_client, _scheduler

    logger.info("medMonitor backend starting — database: %s", settings.database_backend)

    # Pre-initialise DB adapter (creates file/pool on first call)
    get_db()

    # Restore AlertService in-memory state from recent DB records
    await alert_service.restore_state()
    logger.info("AlertService state restored from DB")

    # Start APScheduler (asyncio-native scheduler)
    cfg = config_service.get_config()
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        alert_service.check_alerts,
        "interval",
        seconds=60,
        id="alert_check",
        max_instances=1,
    )
    _scheduler.add_job(
        imap_service.check_inbox,
        "interval",
        seconds=cfg.email.imap.check_interval_seconds,
        id="imap_check",
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "APScheduler started — alert_check every 60s, imap_check every %ds",
        cfg.email.imap.check_interval_seconds,
    )

    # Start MQTT client — pass the running event loop so the background
    # Paho thread can schedule async callbacks via run_coroutine_threadsafe
    loop = asyncio.get_running_loop()
    _mqtt_client = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
    _mqtt_client.start(loop=loop)
    logger.info("MQTT client started (broker: %s:%d)", settings.mqtt_host, settings.mqtt_port)

    yield

    # ---- Shutdown ----
    if _mqtt_client:
        _mqtt_client.stop()
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    await close_db()
    logger.info("medMonitor backend shut down cleanly")


# CORS origins come from the env var CORS_ORIGINS (comma-separated)
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app = FastAPI(
    title=settings.app_name,
    description="Monitoraggio temperatura ZigBee per celle frigorifere",
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router.router)
app.include_router(thresholds_router.router)
app.include_router(readings_router.router)
app.include_router(sensors_router.router)
app.include_router(alerts_router.router)
app.include_router(demo_router.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "database_backend": settings.database_backend,
        "version": "0.5.0",
        "mqtt_connected": _mqtt_client is not None and _mqtt_client.is_connected,
        "scheduler_running": _scheduler is not None and _scheduler.running,
    }
