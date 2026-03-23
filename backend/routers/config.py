"""Config router — GET/PATCH /api/config, test-email, test-imap, switch-database."""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.config_model import AppConfig, ConfigPatch
from backend.services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=AppConfig)
async def get_config():
    """Return current application configuration."""
    return config_service.get_config()


@router.patch("", response_model=AppConfig)
async def patch_config(patch: ConfigPatch):
    """Update runtime configuration parameters."""
    updates = patch.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return config_service.update_config(updates)


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
