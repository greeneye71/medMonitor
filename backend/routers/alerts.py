"""Alerts router — GET /api/alerts, POST /api/alerts/test."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.models.alert import Alert, AlertTestRequest
from backend.dependencies import get_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert])
async def get_alerts(
    zone: str | None = Query(None),
    level: str | None = Query(None, description="WARNING or CRITICAL"),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get alert history with optional filters."""
    db = get_db()
    return await db.get_alerts(
        zone=zone, level=level, from_dt=from_dt, to_dt=to_dt, limit=limit,
    )


@router.post("/test")
async def test_alert(request: AlertTestRequest):
    """Send a test alert email."""
    from backend.services.config_service import config_service

    config = config_service.get_config()
    smtp = config.email.smtp

    if not smtp.host or not smtp.user:
        raise HTTPException(status_code=400, detail="SMTP non configurato")

    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        msg = MIMEText(
            "Questo è un allarme di test da medMonitor.\n\n"
            "Se ricevi questa email, il sistema di notifiche è configurato correttamente."
        )
        msg["Subject"] = "[medMonitor] [TEST] Allarme di test"
        msg["From"] = smtp.user
        msg["To"] = request.email

        await aiosmtplib.send(
            msg,
            hostname=smtp.host,
            port=smtp.port,
            username=smtp.user,
            password=smtp.password,
            start_tls=smtp.use_tls,
        )
        return {"status": "ok", "message": f"Email di test inviata a {request.email}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invio fallito: {e}")
