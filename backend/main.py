"""medMonitor — FastAPI backend entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.dependencies import close_db
from backend.routers import config as config_router
from backend.routers import thresholds as thresholds_router
from backend.routers import readings as readings_router
from backend.routers import sensors as sensors_router
from backend.routers import alerts as alerts_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "medMonitor backend starting — database: %s",
        settings.database_backend,
    )
    yield
    await close_db()
    logger.info("medMonitor backend shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Monitoraggio temperatura ZigBee per celle frigorifere",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8050"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router.router)
app.include_router(thresholds_router.router)
app.include_router(readings_router.router)
app.include_router(sensors_router.router)
app.include_router(alerts_router.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "database_backend": settings.database_backend,
        "version": "0.2.0",
    }
