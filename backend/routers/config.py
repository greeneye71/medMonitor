"""Config router — GET/PATCH /api/config, test-email, test-imap, switch-database.

Also provides /api/zones — zone CRUD endpoints.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.config_model import AppConfig, ConfigPatch, ZoneThresholds
from backend.services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

# ---------------------------------------------------------------------------
# Zone router — /api/zones
# ---------------------------------------------------------------------------

zones_router = APIRouter(prefix="/api/zones", tags=["zones"])


class ZoneCreate(BaseModel):
    name: str
    color: str
    threshold_min: float
    threshold_max: float


@zones_router.get("")
async def list_zones():
    """List all zones with thresholds and colors."""
    try:
        cfg = config_service.get_config()
        result = []
        for zone_name, zone_thresh in cfg.thresholds.defaults.items():
            result.append({
                "name": zone_name,
                "color": cfg.zone_colors.get(zone_name, "#64748b"),
                "threshold_min": zone_thresh.min,
                "threshold_max": zone_thresh.max,
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_zones failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@zones_router.post("")
async def create_or_update_zone(body: ZoneCreate):
    """Upsert a zone with thresholds and color (create or update if already exists)."""
    try:
        config_service.update_threshold_defaults(
            {body.name: ZoneThresholds(min=body.threshold_min, max=body.threshold_max)}
        )
        config_service.update_zone_color(body.name, body.color)
        return {"name": body.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_or_update_zone failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@zones_router.delete("/{zone_name}")
async def delete_zone(zone_name: str):
    """Delete a zone. Returns 409 if sensors are assigned."""
    try:
        from backend.paths import data_file
        sensors_file = data_file("sensors.json")
        if sensors_file.exists():
            sensors = json.loads(sensors_file.read_text(encoding="utf-8"))
            if any(s.get("zone") == zone_name for s in sensors.values()):
                raise HTTPException(
                    status_code=409,
                    detail=f"Zone '{zone_name}' ha sensori assegnati. Riassegna prima i sensori."
                )
        config_service.delete_threshold_default(zone_name)
        config_service.delete_zone_color(zone_name)
        return {"deleted": zone_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_zone failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=AppConfig)
async def get_config():
    """Return current application configuration."""
    try:
        return config_service.get_config()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_config failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("", response_model=AppConfig)
async def patch_config(patch: ConfigPatch):
    """Update runtime configuration parameters."""
    try:
        updates = patch.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        updated = config_service.update_config(updates)
        # Validate result is a valid AppConfig
        AppConfig.model_validate(updated.model_dump())
        return updated
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Config validation failed: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("patch_config failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-email")
async def test_email(payload: dict):
    """Send a test email via SMTP."""
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Field 'email' is required")

    config = config_service.get_config()
    smtp = config.email.smtp

    if not smtp.host or not smtp.user:
        raise HTTPException(status_code=400, detail="SMTP not configured")

    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        msg = MIMEText("Test email da medMonitor. La configurazione SMTP funziona correttamente.")
        msg["Subject"] = "[medMonitor] Test configurazione email"
        msg["From"] = smtp.user
        msg["To"] = email

        await aiosmtplib.send(
            msg,
            hostname=smtp.host,
            port=smtp.port,
            username=smtp.user,
            password=smtp.password,
            start_tls=smtp.use_tls,
        )
        return {"status": "ok", "message": f"Email di test inviata a {email}"}

    except Exception as e:
        logger.error("Test email failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Invio email fallito: {e}")


@router.post("/test-imap")
async def test_imap():
    """Test IMAP connection."""
    config = config_service.get_config()
    imap = config.email.imap

    if not imap.host or not imap.user:
        raise HTTPException(status_code=400, detail="IMAP not configured")

    try:
        import imaplib

        if imap.use_ssl:
            conn = imaplib.IMAP4_SSL(imap.host, imap.port)
        else:
            conn = imaplib.IMAP4(imap.host, imap.port)

        conn.login(imap.user, imap.password)
        status, folders = conn.select(imap.folder, readonly=True)
        message_count = int(folders[0]) if status == "OK" else 0
        conn.logout()

        return {
            "status": "ok",
            "message": f"Connessione IMAP riuscita. {message_count} messaggi in {imap.folder}",
        }

    except Exception as e:
        logger.error("Test IMAP failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Connessione IMAP fallita: {e}")


@router.post("/switch-database")
async def switch_database(payload: dict):
    """Switch database backend (tinyflux / timescale)."""
    try:
        new_backend = payload.get("backend")
        if new_backend not in ("tinyflux", "timescale"):
            raise HTTPException(
                status_code=400,
                detail="Field 'backend' must be 'tinyflux' or 'timescale'",
            )

        config_service.update_config({"database_backend": new_backend})
        return {
            "status": "ok",
            "message": f"Backend cambiato a {new_backend}. Riavviare il servizio per applicare.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("switch_database failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
