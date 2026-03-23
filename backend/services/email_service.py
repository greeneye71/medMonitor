"""Email service — SMTP sending for alerts and notifications."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.services.config_service import config_service

logger = logging.getLogger(__name__)

# Jinja2 template environment
_template_env = Environment(
    loader=FileSystemLoader("backend/templates"),
    autoescape=select_autoescape(["html"]),
)


async def send_alert_email(alert: dict[str, Any]) -> None:
    """Send alert email to all configured recipients."""
    config = config_service.get_config()
    smtp = config.email.smtp

    if not smtp.host or not smtp.user or not smtp.recipients:
        logger.warning("SMTP not configured, skipping alert email")
        return

    recipients = [r.strip() for r in smtp.recipients.split(",") if r.strip()]
    if not recipients:
        return

    # Build subject
    level = alert["level"]
    if level == "CRITICAL":
        subject = f"[ALLARME CRITICO] {alert['zone']} — {alert['temperature']:.1f}°C"
    else:
        subject = f"[AVVISO] {alert['zone']} — {alert['temperature']:.1f}°C"

    # Build HTML body
    try:
        template = _template_env.get_template("alert_email.html")
        html_body = template.render(alert=alert)
    except Exception:
        # Fallback to plain text
        html_body = None

    text_body = alert.get("message", str(alert))

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[medMonitor] {subject}"
    msg["From"] = smtp.user
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Send
    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp.host,
            port=smtp.port,
            username=smtp.user,
            password=smtp.password,
            start_tls=smtp.use_tls,
        )
        logger.info("Alert email sent to %s: %s", recipients, subject)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        raise
