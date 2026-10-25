"""Web layer: shared Jinja2 environment and render helper."""
from datetime import datetime
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import __version__
from app.db import local, parse, utcnow

WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

KIND_LABEL = {"fridge": "Frigorifero", "freezer": "Congelatore"}
EVENT_LABEL = {
    "TEMP_OPEN": "Allarme temperatura", "TEMP_CLOSE": "Temperatura rientrata",
    "OFFLINE_OPEN": "Sensore non risponde", "OFFLINE_CLOSE": "Sensore di nuovo online",
    "BATTERY_OPEN": "Batteria scarica", "BATTERY_CLOSE": "Batteria sostituita",
    "MUTE": "Silenziamento", "SENSOR_ADDED": "Sensore aggiunto",
    "SENSOR_REMOVED": "Sensore rimosso", "EMAIL_ERROR": "Errore email",
    "ARCHIVE": "Archiviazione", "CONFIG": "Configurazione",
    "GATEWAY_OFFLINE_OPEN": "Gateway non raggiungibile",
    "GATEWAY_OFFLINE_CLOSE": "Gateway di nuovo raggiungibile", "SENSOR_MOVED": "Sensore spostato",
}
EVENT_TONE = {"TEMP_OPEN": "alarm", "EMAIL_ERROR": "alarm", "OFFLINE_OPEN": "offline",
              "BATTERY_OPEN": "warn", "TEMP_CLOSE": "ok", "OFFLINE_CLOSE": "ok",
              "BATTERY_CLOSE": "ok", "GATEWAY_OFFLINE_OPEN": "offline",
              "GATEWAY_OFFLINE_CLOSE": "ok"}


def num(v, digits: int = 1) -> str:
    """Italian decimal formatting: 4.5 -> '4,5'."""
    if v is None:
        return "—"
    return f"{v:.{digits}f}".replace(".", ",").replace("-", "−")


def ago(ts, now: datetime | None = None) -> str:
    dt = parse(ts) if isinstance(ts, str) else ts
    if dt is None:
        return "mai"
    minutes = int(((now or utcnow()) - dt).total_seconds() // 60)
    if minutes < 1:
        return "adesso"
    if minutes < 60:
        return f"{minutes} min fa"
    if minutes < 48 * 60:
        return f"{minutes // 60} h fa"
    return local(dt, "%d/%m %H:%M")


def size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}".replace(".", ",")
        n /= 1024
    return str(n)


templates.env.filters.update(local=local, num=num, ago=ago, size=size)
templates.env.globals.update(KIND_LABEL=KIND_LABEL, EVENT_LABEL=EVENT_LABEL,
                             EVENT_TONE=EVENT_TONE, version=__version__)


def flash(request: Request, message: str, tone: str = "ok") -> None:
    request.session["flash"] = {"message": message, "tone": tone}


def render(request: Request, name: str, status_code: int = 200, **ctx):
    ctx.setdefault("flash", request.session.pop("flash", None))
    ctx.setdefault("is_admin", bool(request.session.get("admin")))
    ctx.setdefault("path", request.url.path)
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
