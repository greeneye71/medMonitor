"""Email outbox: templates, queueing, SMTP delivery with retry."""
import asyncio
import html
import logging
from datetime import datetime, timedelta
from email.message import EmailMessage

import aiosmtplib

from app import settings
from app.db import Database, iso, local, parse

log = logging.getLogger(__name__)

MAX_FAST_ATTEMPTS = 5
SLOW_RETRY = timedelta(minutes=10)

COLORS = {"alarm": "#C62828", "ok": "#2E7D32", "warn": "#B26A00", "info": "#455A64"}


def _fmt(v) -> str:
    return "—" if v is None else f"{v:.1f}".replace(".", ",")


def render(kind: str, sensor: dict | None = None, now: datetime | None = None, **ctx):
    """Return (subject, text, html) for an email of the given kind."""
    s = sensor or {}
    name = s.get("name", "")
    when = local(now) if now else ""
    rng = f"{_fmt(s.get('min_c'))} … {_fmt(s.get('max_c'))} °C"
    if kind == "temp_open":
        head, color = "ALLARME TEMPERATURA", "alarm"
        title = f"{name} {_fmt(ctx.get('value'))} °C"
        lines = [f"Il sensore «{name}» è fuori soglia.",
                 f"Temperatura attuale: {_fmt(ctx.get('value'))} °C",
                 f"Intervallo ammesso: {rng}",
                 f"Fuori soglia da: {local(ctx.get('since'))}"]
    elif kind == "temp_close":
        head, color = "TEMPERATURA RIENTRATA", "ok"
        title = f"{name} {_fmt(ctx.get('value'))} °C"
        lines = [f"Il sensore «{name}» è tornato nell'intervallo {rng}.",
                 f"Temperatura attuale: {_fmt(ctx.get('value'))} °C",
                 f"Durata dell'anomalia: {ctx.get('duration', '—')}"]
    elif kind == "offline_open":
        head, color = "SENSORE NON RISPONDE", "warn"
        title = name
        lines = [f"Il sensore «{name}» non invia dati da più di {ctx.get('minutes')} minuti.",
                 f"Ultimo dato ricevuto: {local(s.get('last_seen_at'))}",
                 "Controllare batteria, distanza dal gateway e stato del gateway."]
    elif kind == "offline_close":
        head, color = "SENSORE DI NUOVO ONLINE", "ok"
        title = name
        lines = [f"Il sensore «{name}» ha ripreso a inviare dati.",
                 f"Temperatura attuale: {_fmt(s.get('last_temp'))} °C"]
    elif kind == "battery_open":
        head, color = "BATTERIA SCARICA", "warn"
        title = f"{name} {s.get('last_battery')}%"
        lines = [f"La batteria del sensore «{name}» è al {s.get('last_battery')}%.",
                 "Sostituire la batteria appena possibile."]
    elif kind == "test":
        head, color = "EMAIL DI PROVA", "info"
        title = ""
        lines = ["Questa è un'email di prova inviata da medMonitor.",
                 "Se la ricevi, la configurazione email è corretta."]
    else:
        raise ValueError(f"tipo email sconosciuto: {kind}")
    subject = f"[medMonitor] {head}" + (f" — {title}" if title else "")
    text = "\n".join([head, ""] + lines + ["", f"medMonitor · {when}"])
    body = "".join(f"<p style='margin:0 0 8px'>{html.escape(str(x))}</p>" for x in lines)
    html_doc = (
        "<div style='font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:auto;"
        "border:1px solid #ddd;border-radius:10px;overflow:hidden'>"
        f"<div style='background:{COLORS[color]};color:#fff;padding:14px 18px;"
        f"font-weight:600;font-size:16px'>{html.escape(head)}</div>"
        f"<div style='padding:16px 18px;color:#222;font-size:14px'>{body}</div>"
        "<div style='padding:10px 18px;color:#888;font-size:12px;border-top:1px solid #eee'>"
        f"medMonitor · {html.escape(when)}</div></div>")
    return subject, text, html_doc


def enqueue(db: Database, now: datetime, subject: str, text: str, html_doc: str) -> None:
    db.execute("INSERT INTO outbox(created_at,subject,body_text,body_html) VALUES(?,?,?,?)",
               (iso(now), subject, text, html_doc))


def notify(db: Database, now: datetime, kind: str, sensor: dict | None = None, **ctx) -> None:
    enqueue(db, now, *render(kind, sensor, now, **ctx))


async def send_email(smtp: dict, recipients: list[str], subject: str, text: str,
                     html_doc: str) -> dict:
    """Send one email. Returns the recipients refused by the server ({} if none).

    aiosmtplib raises only when *every* recipient is refused; a partial refusal is reported
    in the return value instead.
    """
    msg = EmailMessage()
    msg["From"] = smtp.get("sender") or smtp.get("user")
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html_doc, subtype="html")
    security = smtp.get("security", "starttls")
    refused, _ = await aiosmtplib.send(
        msg, hostname=smtp["host"], port=int(smtp.get("port") or 587),
        username=smtp.get("user") or None, password=smtp.get("password") or None,
        use_tls=security == "ssl", start_tls=security == "starttls", timeout=30)
    return refused


def send_now(smtp: dict, recipients: list[str], subject: str, text: str, html_doc: str,
             sender=send_email) -> dict:
    """Synchronous send. Returns the refused recipients ({} if all accepted)."""
    return asyncio.run(sender(smtp, recipients, subject, text, html_doc)) or {}


def refused_text(refused: dict) -> str:
    return ", ".join(f"{addr} ({err[0]} {err[1]})"[:200] for addr, err in refused.items())


def process_outbox(db: Database, now: datetime, sender=send_email) -> int:
    """Try to send pending emails. Returns number sent. Never raises."""
    smtp = settings.get(db, "smtp")
    recipients = settings.get(db, "recipients")
    if not smtp.get("host") or not recipients:
        return 0
    sent = 0
    for row in db.query("SELECT * FROM outbox WHERE sent_at IS NULL ORDER BY id"):
        last = parse(row["last_attempt_at"])
        if row["attempts"] >= MAX_FAST_ATTEMPTS and last and now - last < SLOW_RETRY:
            continue
        try:
            refused = send_now(smtp, recipients, row["subject"], row["body_text"],
                               row["body_html"], sender)
        except Exception as exc:  # noqa: BLE001 - any SMTP/network failure is retried
            attempts = row["attempts"] + 1
            log.warning("invio email %s fallito (tentativo %s): %s", row["id"], attempts, exc)
            db.execute("UPDATE outbox SET attempts=?, last_error=?, last_attempt_at=? WHERE id=?",
                       (attempts, str(exc)[:500], iso(now), row["id"]))
            if attempts == MAX_FAST_ATTEMPTS:
                db.add_event(now, None, "EMAIL_ERROR",
                             f"Email non inviata dopo {attempts} tentativi: {row['subject']} "
                             f"({str(exc)[:200]})")
            continue
        db.execute("UPDATE outbox SET sent_at=?, last_attempt_at=? WHERE id=?",
                   (iso(now), iso(now), row["id"]))
        if refused:
            # delivered to the others: no retry (it would duplicate), but make it visible
            log.warning("email %s: destinatari rifiutati %s", row["id"], refused)
            db.add_event(now, None, "EMAIL_ERROR",
                         f"Destinatari rifiutati dal server: {refused_text(refused)} "
                         f"— {row['subject']}")
        sent += 1
    return sent


def pending_count(db: Database) -> int:
    return db.one("SELECT COUNT(*) n FROM outbox WHERE sent_at IS NULL")["n"]


def failing_count(db: Database) -> int:
    return db.one("SELECT COUNT(*) n FROM outbox WHERE sent_at IS NULL AND attempts>=?",
                  (MAX_FAST_ATTEMPTS,))["n"]
