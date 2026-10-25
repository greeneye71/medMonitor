"""Public pages: overview, history, events, login."""
import csv
import io
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from app import notifier, settings
from app.archive import csv_text
from app.auth import verify_password
from app.db import LOCAL_TZ, iso, local, parse, utcnow
from app.monitor import sensor_status
from app.web import EVENT_LABEL, render

router = APIRouter()

PERIODS = {"24h": ("24 ore", timedelta(hours=24)), "7d": ("7 giorni", timedelta(days=7)),
           "30d": ("30 giorni", timedelta(days=30))}
PAGE_SIZE = 50


# ---------- overview ----------

def range_position(temp, min_c, max_c) -> float | None:
    """Marker position (0–100 %) on a strip where the allowed band covers 25 %–75 %."""
    if temp is None:
        return None
    span = (max_c - min_c) or 1.0
    lo = min_c - span / 2
    pos = (temp - lo) / (span * 2) * 100
    return max(0.0, min(100.0, pos))


def sparkline(samples: list[dict], min_c: float, max_c: float, start: datetime,
              end: datetime, w: int = 240, h: int = 44) -> dict | None:
    """Precompute an inline SVG sparkline: polyline points plus the threshold band."""
    if not samples:
        return None
    temps = [s["temp_c"] for s in samples]
    lo, hi = min(temps + [min_c]), max(temps + [max_c])
    pad = (hi - lo) * 0.1 or 1.0
    lo, hi = lo - pad, hi + pad
    total = (end - start).total_seconds() or 1

    def y(t):
        return round(h - (t - lo) / (hi - lo) * h, 1)

    pts = []
    for s in samples:
        x = (parse(s["ts"]) - start).total_seconds() / total * w
        pts.append(f"{round(x, 1)},{y(s['temp_c'])}")
    last = pts[-1].split(",")
    return {"w": w, "h": h, "points": " ".join(pts), "band_y": y(max_c),
            "band_h": round(y(min_c) - y(max_c), 1), "last_x": last[0], "last_y": last[1]}


def overview_context(request: Request) -> dict:
    db = request.app.state.db
    now = utcnow()
    offline_min = int(settings.get(db, "alarm")["offline_minutes"])
    start = now - timedelta(hours=24)
    states = {r["sensor_id"]: r for r in db.query("SELECT * FROM alert_state")}
    cards = []
    for s in db.query("SELECT * FROM sensors WHERE active=1 ORDER BY name COLLATE NOCASE"):
        st = states.get(s["ieee"])
        samples = db.query("SELECT ts, temp_c FROM samples WHERE sensor_id=? AND ts>=? ORDER BY ts",
                           (s["ieee"], iso(start)))
        muted_until = parse(s["muted_until"])
        cards.append({
            **s,
            "status": sensor_status(s, st, now, offline_min),
            "battery_low": bool(st and st["battery_open"]),
            "muted_until": muted_until if muted_until and muted_until > now else None,
            "pos": range_position(s["last_temp"], s["min_c"], s["max_c"]),
            "spark": sparkline(samples, s["min_c"], s["max_c"], start, now),
        })

    mqtt = request.app.state.mqtt
    gateways = request.app.state.gateways
    known = {g.id for g in gateways}
    sections = []
    for i, g in enumerate(gateways):
        bs = mqtt.states.get(g.id) if mqtt is not None else None
        online = mqtt is None or bool(mqtt.connected and bs is not None and bs.online)
        since = (bs.offline_since if bs is not None else None) or             (mqtt.started_at if mqtt is not None else None)
        down_minutes = int((now - since).total_seconds() // 60) if not online and since else None
        # Sensors of a gateway no longer configured are shown with the first one.
        sec_cards = [c for c in cards
                     if c["gateway_id"] == g.id or (i == 0 and c["gateway_id"] not in known)]
        sections.append({"gateway": g, "online": online, "down_minutes": down_minutes,
                         "cards": sec_cards})
    multi = len(gateways) > 1

    alarms = sum(c["status"] == "alarm" for c in cards)
    offline = sum(c["status"] == "offline" for c in cards)
    gw_down = sum(1 for sec in sections if not sec["online"] and sec["cards"])
    failing = notifier.failing_count(db)
    email_ready = bool(settings.get(db, "smtp")["host"] and settings.get(db, "recipients"))
    alarm_text = (f"{alarms} allarm{'e' if alarms == 1 else 'i'} temperatura attiv"
                  f"{'o' if alarms == 1 else 'i'}")
    offline_text = (f"{offline} sensor{'e' if offline == 1 else 'i'} non risponde"
                    f"{'' if offline == 1 else 'no'}")
    gw_text = f"{gw_down} gateway non raggiungibil{'e' if gw_down == 1 else 'i'}"
    if multi and (alarms or gw_down or offline):
        parts = [t for n, t in ((alarms, alarm_text), (gw_down, gw_text), (offline, offline_text))
                 if n]
        band = ("alarm" if alarms else "offline", " · ".join(parts))
    elif alarms:
        band = ("alarm", alarm_text)
    elif not multi and sections and not sections[0]["online"]:
        band = ("offline", "Gateway non raggiungibile: nessun dato in arrivo dai sensori")
    elif offline:
        band = ("offline", offline_text)
    elif failing:
        band = ("warn", "Email di allarme non inviate: controlla le impostazioni email")
    elif cards and not email_ready:
        band = ("warn", "Email di allarme non configurate: nessuno riceverà gli avvisi")
    elif not cards:
        band = ("muted", "Nessun sensore configurato")
    else:
        band = ("ok", "Tutto regolare")
    return {"cards": cards, "sections": sections, "multi": multi, "band": band, "now": now}


@router.get("/")
def overview(request: Request):
    return render(request, "overview.html", **overview_context(request))


@router.get("/partials/cards")
def overview_cards(request: Request):
    return render(request, "_cards.html", **overview_context(request))


# ---------- history ----------

def _local_date(value: str | None) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ) if value else None
    except ValueError:
        return None


def history_query(request: Request, sensor: str | None, period: str, from_: str | None,
                  to: str | None) -> dict:
    db = request.app.state.db
    sensors = db.query("SELECT * FROM sensors WHERE active=1 ORDER BY name COLLATE NOCASE")
    if sensor:
        # removed sensors keep their history: look them up too, never fall back to another one
        current = db.one("SELECT * FROM sensors WHERE ieee=?", (sensor,))
        if current is None:
            raise HTTPException(404, "Sensore non trovato")
        if not current["active"]:
            sensors.append(current)
    else:
        current = sensors[0] if sensors else None
    now = utcnow()
    if period == "custom":
        start, end = _local_date(from_), _local_date(to)
        if start is None or end is None or end < start:
            period, start, end = "24h", now - PERIODS["24h"][1], now
        else:
            end = end + timedelta(days=1)
    else:
        period = period if period in PERIODS else "24h"
        start, end = now - PERIODS[period][1], now
    samples = []
    if current:
        samples = db.query("SELECT ts, temp_c, battery FROM samples WHERE sensor_id=? AND ts>=? "
                           "AND ts<? ORDER BY ts", (current["ieee"], iso(start), iso(end)))
    return {"sensors": sensors, "sensor": current, "period": period, "start": start,
            "end": end, "samples": samples, "periods": PERIODS,
            "from_value": start.astimezone(LOCAL_TZ).strftime("%Y-%m-%d"),
            "to_value": (end - timedelta(seconds=1)).astimezone(LOCAL_TZ).strftime("%Y-%m-%d")}


def _gw_ctx(request: Request) -> dict:
    gws = request.app.state.gateways
    return {"multi": len(gws) > 1, "gw_names": {g.id: g.name for g in gws}}


def stats(samples: list[dict], min_c: float, max_c: float) -> dict | None:
    if not samples:
        return None
    temps = [s["temp_c"] for s in samples]
    inside = sum(min_c <= t <= max_c for t in temps)
    return {"min": min(temps), "max": max(temps), "mean": sum(temps) / len(temps),
            "in_range": inside / len(temps) * 100, "count": len(temps)}


@router.get("/storico")
def history(request: Request, sensor: str | None = None, period: str = "24h",
            from_: str | None = None, to: str | None = None):
    from_ = from_ or request.query_params.get("from")
    ctx = history_query(request, sensor, period, from_, to)
    s = ctx["sensor"]
    ctx["stats"] = stats(ctx["samples"], s["min_c"], s["max_c"]) if s else None
    ctx["chart"] = {
        "points": [[int(parse(x["ts"]).timestamp() * 1000), x["temp_c"]] for x in ctx["samples"]],
        "min": s["min_c"] if s else None, "max": s["max_c"] if s else None,
        "start": int(ctx["start"].timestamp() * 1000), "end": int(ctx["end"].timestamp() * 1000),
    }
    ctx["csv_query"] = str(request.url.query)
    ctx.update(_gw_ctx(request))
    return render(request, "history.html", **ctx)


@router.get("/storico.csv")
def history_csv(request: Request, sensor: str | None = None, period: str = "24h",
                to: str | None = None):
    ctx = history_query(request, sensor, period, request.query_params.get("from"), to)
    s = ctx["sensor"]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["data_ora", "sensore", "temperatura_c", "batteria"])
    for x in ctx["samples"]:
        w.writerow([local(x["ts"], "%Y-%m-%d %H:%M"), csv_text(s["name"]),
                    f"{x['temp_c']:.1f}".replace(".", ","),
                    "" if x["battery"] is None else x["battery"]])
    # Header values must be latin-1: keep the filename plain ASCII.
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", s["name"] if s else "vuoto").strip("_") or "sensore"
    name = f"storico_{base}_{re.sub(r'[^0-9-]', '', ctx['from_value'])}.csv"
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ---------- events ----------

@router.get("/eventi")
def events(request: Request, sensor: str = "", type: str = "", page: int = 1):  # noqa: A002
    db = request.app.state.db
    where, params = [], []
    if sensor:
        where.append("e.sensor_id=?")
        params.append(sensor)
    if type in EVENT_LABEL:
        where.append("e.type=?")
        params.append(type)
    sql_where = f"WHERE {' AND '.join(where)}" if where else ""
    total = db.one(f"SELECT COUNT(*) n FROM events e {sql_where}", params)["n"]
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(max(1, page), pages)
    rows = db.query(
        f"SELECT e.*, s.name AS sensor_name, COALESCE(s.gateway_id, CASE WHEN e.type "
        f"LIKE 'GATEWAY%' THEN CAST(e.value AS INTEGER) END) AS gw_id FROM events e "
        f"LEFT JOIN sensors s "
        f"ON s.ieee=e.sensor_id {sql_where} ORDER BY e.id DESC LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE])
    sensors = db.query("SELECT ieee, name FROM sensors ORDER BY name COLLATE NOCASE")
    return render(request, "events.html", rows=rows, sensors=sensors, sensor=sensor,
                  type=type if type in EVENT_LABEL else "", page=page, pages=pages,
                  total=total, **_gw_ctx(request))


# ---------- login ----------

def _safe_next(target: str | None) -> str:
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return "/impostazioni"


@router.get("/login")
def login_form(request: Request, next: str = "/impostazioni"):  # noqa: A002
    if request.session.get("admin"):
        return RedirectResponse(_safe_next(next), status_code=303)
    return render(request, "login.html", next=_safe_next(next), error=None)


@router.post("/login")
def login(request: Request, password: str = Form(""), next: str = Form("/impostazioni")):  # noqa: A002
    stored = settings.get(request.app.state.db, "admin_password_hash")
    if not verify_password(password, stored):
        return render(request, "login.html", status_code=200, next=_safe_next(next),
                      error="Password non corretta.")
    request.session["admin"] = True
    return RedirectResponse(_safe_next(next), status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
