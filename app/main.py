"""FastAPI app: DB, MQTT, scheduler and web routes.

Run with: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8090
"""
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import archive, monitor, notifier, settings
from app.auth import NotAuthenticated, hash_password
from app.db import LOCAL_TZ, Database, utcnow
from app.mqtt import MqttService
from app.web import WEB_DIR
from app.web.admin import router as admin_router
from app.web.routes import router as public_router

log = logging.getLogger("medmonitor")


def _job(name, fn):
    def run():
        try:
            fn()
        except Exception:  # noqa: BLE001 - a failing job must not stop the scheduler
            log.exception("job %s fallito", name)
    return run


def build_scheduler(app: FastAPI) -> BackgroundScheduler:
    db = app.state.db
    sch = BackgroundScheduler(timezone=LOCAL_TZ)
    sch.add_job(_job("campionamento", lambda: monitor.run_cycle(db, utcnow())),
                "cron", minute="*/10", id="sampling", coalesce=True, max_instances=1)
    sch.add_job(_job("email", lambda: notifier.process_outbox(db, utcnow())),
                "interval", minutes=1, id="outbox", coalesce=True, max_instances=1)
    sch.add_job(_job("archivio", lambda: archive.archive_old(
                db, app.state.data_dir / "archive", utcnow())),
                "cron", hour=3, minute=0, id="archive")
    sch.add_job(_job("vacuum", lambda: db.execute("VACUUM")),
                "cron", day_of_week="sun", hour=3, minute=30, id="vacuum")
    return sch


def create_app(data_dir: str | Path | None = None, start_services: bool = True,
               z2m_path: str | Path | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    data_dir = Path(data_dir or os.environ.get("DATA_DIR", "data"))
    db = Database(data_dir / "medmonitor.db")

    if not settings.get(db, "admin_password_hash"):
        settings.set(db, "admin_password_hash",
                     hash_password(os.environ.get("ADMIN_PASSWORD") or "admin"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_services:
            app.state.mqtt = MqttService(db, os.environ.get("MQTT_HOST", "mosquitto"),
                                         int(os.environ.get("MQTT_PORT", "1883")))
            app.state.mqtt.start()
            app.state.scheduler = build_scheduler(app)
            app.state.scheduler.start()
        yield
        if app.state.scheduler:
            app.state.scheduler.shutdown(wait=False)
        if app.state.mqtt:
            app.state.mqtt.stop()
        db.close()

    app = FastAPI(title="medMonitor", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db = db
    app.state.mqtt = None
    app.state.scheduler = None
    app.state.data_dir = data_dir
    app.state.z2m_path = Path(z2m_path or os.environ.get("Z2M_CONFIG", "/z2m/configuration.yaml"))

    app.add_middleware(SessionMiddleware,
                       secret_key=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
                       session_cookie="medmonitor", max_age=8 * 3600)
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(public_router)
    app.include_router(admin_router)

    @app.exception_handler(NotAuthenticated)
    async def _login_redirect(request: Request, exc: NotAuthenticated):
        return RedirectResponse(f"/login?next={exc.args[0]}", status_code=303)

    @app.get("/health")
    def health():
        try:
            db.one("SELECT 1")
            db_ok = "ok"
        except Exception as exc:  # noqa: BLE001
            db_ok = str(exc)
        mqtt = app.state.mqtt
        sch = app.state.scheduler
        return JSONResponse({
            "db": db_ok,
            "mqtt_connected": bool(mqtt and mqtt.connected),
            "gateway_online": bool(mqtt and mqtt.state.online),
            "scheduler_running": bool(sch and sch.running),
            "outbox_pending": notifier.pending_count(db),
        })

    return app
