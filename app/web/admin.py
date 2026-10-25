"""Password-protected settings pages (/impostazioni/...).

Handlers are plain `def` (run in the threadpool) because send_now uses asyncio.run.
"""
import math
import re
import time
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from app import archive, gateways, notifier, settings, z2m_config
from app.auth import hash_password, require_admin, verify_password
from app.db import iso, utcnow
from app.web import KIND_LABEL, flash, render

router = APIRouter(prefix="/impostazioni", dependencies=[Depends(require_admin)])

TABS = [("sensori", "Sensori"), ("email", "Email"), ("gateway", "Gateway"),
        ("allarmi", "Allarmi"), ("archivio", "Archivio"), ("sicurezza", "Password")]
MUTE_HOURS = (1, 4, 24)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NAME_MAX = 60
IP_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")


def _clean_name(value: str) -> str:
    """Sensor name without control characters (they would break email headers)."""
    return " ".join("".join(c if c.isprintable() else " " for c in value).split())[:NAME_MAX]


def _back(tab: str) -> RedirectResponse:
    return RedirectResponse(f"/impostazioni/{tab}", status_code=303)


def _float(value: str) -> float | None:
    try:
        n = float(value.strip().replace(",", ".").replace("−", "-"))
    except (ValueError, AttributeError):
        return None
    return n if math.isfinite(n) else None


def _int(value: str, lo: int, hi: int) -> int | None:
    try:
        n = int(str(value).strip())
    except ValueError:
        return None
    return n if lo <= n <= hi else None


def _thresholds(min_c: str, max_c: str) -> tuple[float, float] | str:
    lo, hi = _float(min_c), _float(max_c)
    if lo is None or hi is None:
        return "Soglie non valide: inserisci due numeri, ad esempio 2 e 8."
    if lo >= hi:
        return "La soglia minima deve essere più bassa della massima."
    if lo < -60 or hi > 60:
        return "Soglie fuori scala: usa valori tra −60 e 60 °C."
    return lo, hi


def _page(request: Request, tab: str, name: str, **ctx):
    return render(request, f"settings/{name}", tabs=TABS, tab=tab, **ctx)


def _mqtt(request: Request):
    return request.app.state.mqtt


@router.get("")
def index():
    return _back("sensori")


# ---------- sensori ----------

def _discovered(request: Request) -> list[dict]:
    return request.app.state.db.query(
        "SELECT d.* FROM discovered d LEFT JOIN sensors s ON s.ieee=d.ieee AND s.active=1 "
        "WHERE s.ieee IS NULL ORDER BY d.first_seen DESC")


def _pairing(request: Request) -> dict:
    """Open permit_join window, if any: {"left": seconds, "name": gateway name}."""
    mqtt = _mqtt(request)
    for gw in request.app.state.gateways if mqtt else []:
        left = int(mqtt.states[gw.id].permit_join_until - time.time()) if gw.id in mqtt.states else 0
        if left > 0:
            return {"left": left, "name": gw.name}
    return {"left": 0, "name": ""}


def _sensor_ctx(request: Request) -> dict:
    db, gws = request.app.state.db, request.app.state.gateways
    pairing = _pairing(request)
    return {"discovered": _discovered(request), "presets": settings.get(db, "presets"),
            "pairing_left": pairing["left"], "pairing_name": pairing["name"],
            "gateways": gws, "multi": len(gws) > 1,
            "gw_names": {g.id: g.name for g in gws}}


@router.get("/sensori")
def sensors_page(request: Request):
    db = request.app.state.db
    return _page(request, "sensori", "sensors.html",
                 sensors=db.query("SELECT * FROM sensors WHERE active=1 "
                                  "ORDER BY name COLLATE NOCASE"),
                 mute_hours=MUTE_HOURS, now=utcnow(), **_sensor_ctx(request))


@router.get("/sensori/rilevati")
def discovered_partial(request: Request):
    return render(request, "settings/_discovered.html", **_sensor_ctx(request))


@router.post("/sensori/abbina")
def pair(request: Request, gateway_id: int = Form(0)):
    mqtt, gws = _mqtt(request), request.app.state.gateways
    gw = gateways.by_id(gws, gateway_id) if gateway_id else gws[0]
    if not gw:
        flash(request, "Gateway non trovato: ricarica la pagina e riprova.", "alarm")
    elif mqtt and mqtt.permit_join(gw.id, 120):
        mqtt.states[gw.id].permit_join_until = time.time() + 120
        where = f" su {gw.name}" if len(gws) > 1 else ""
        flash(request, f"Abbinamento aperto{where} per 2 minuti: premi il tasto sul sensore.")
    else:
        flash(request, "Gateway non raggiungibile: impossibile avviare l'abbinamento.", "alarm")
    return _back("sensori")


@router.post("/sensori/aggiungi")
def add_sensor(request: Request, ieee: str = Form(...), name: str = Form(""),
               kind: str = Form("fridge"), min_c: str = Form(""), max_c: str = Form("")):
    db = request.app.state.db
    name, kind = _clean_name(name), kind if kind in KIND_LABEL else "fridge"
    found = db.one("SELECT * FROM discovered WHERE ieee=?", (ieee,))
    if not found:
        flash(request, "Sensore non trovato tra quelli rilevati.", "alarm")
        return _back("sensori")
    th = _thresholds(min_c, max_c)
    if isinstance(th, str) or not name:
        flash(request, th if isinstance(th, str) else "Inserisci un nome per il sensore.", "alarm")
        return _back("sensori")
    now = utcnow()
    seen = found["last_seen"]                 # real time of last reading, not "now"
    db.execute(
        "INSERT INTO sensors(ieee,name,kind,min_c,max_c,active,last_temp,last_seen_at,created_at,"
        "gateway_id) VALUES(?,?,?,?,?,1,?,?,?,?) ON CONFLICT(ieee) DO UPDATE SET name=excluded.name, "
        "kind=excluded.kind, min_c=excluded.min_c, max_c=excluded.max_c, active=1, "
        "muted_until=NULL, last_temp=COALESCE(excluded.last_temp, sensors.last_temp), "
        "last_seen_at=COALESCE(excluded.last_seen_at, sensors.last_seen_at), "
        "gateway_id=excluded.gateway_id",
        (ieee, name, kind, th[0], th[1], found["last_temp"], seen, iso(now), found["gateway_id"]))
    db.add_event(now, ieee, "SENSOR_ADDED", f"Sensore «{name}» aggiunto ({th[0]} … {th[1]} °C)")
    flash(request, f"Sensore «{name}» aggiunto.")
    return _back("sensori")


@router.post("/sensori/{ieee}/modifica")
def edit_sensor(request: Request, ieee: str, name: str = Form(""), kind: str = Form("fridge"),
                min_c: str = Form(""), max_c: str = Form("")):
    db = request.app.state.db
    name = _clean_name(name)
    sensor = db.one("SELECT * FROM sensors WHERE ieee=? AND active=1", (ieee,))
    th = _thresholds(min_c, max_c)
    if not sensor:
        flash(request, "Sensore non trovato.", "alarm")
    elif isinstance(th, str) or not name:
        flash(request, th if isinstance(th, str) else "Il nome non può essere vuoto.", "alarm")
    else:
        kind = kind if kind in KIND_LABEL else sensor["kind"]
        db.execute("UPDATE sensors SET name=?, kind=?, min_c=?, max_c=? WHERE ieee=?",
                   (name, kind, th[0], th[1], ieee))
        db.add_event(utcnow(), ieee, "CONFIG",
                     f"Sensore «{name}»: soglie {th[0]} … {th[1]} °C")
        flash(request, f"Sensore «{name}» salvato.")
    return _back("sensori")


@router.post("/sensori/{ieee}/silenzia")
def mute_sensor(request: Request, ieee: str, hours: int = Form(0)):
    db = request.app.state.db
    sensor = db.one("SELECT * FROM sensors WHERE ieee=?", (ieee,))
    if sensor:
        now = utcnow()
        if hours in MUTE_HOURS:
            db.execute("UPDATE sensors SET muted_until=? WHERE ieee=?",
                       (iso(now + timedelta(hours=hours)), ieee))
            msg = f"Email silenziate per {hours} h"
        else:
            db.execute("UPDATE sensors SET muted_until=NULL WHERE ieee=?", (ieee,))
            msg = "Silenziamento annullato"
        db.add_event(now, ieee, "MUTE", f"{msg} per «{sensor['name']}»")
        flash(request, f"{msg} per «{sensor['name']}».")
    return _back("sensori")


@router.post("/sensori/{ieee}/rimuovi")
def remove_sensor(request: Request, ieee: str):
    db = request.app.state.db
    sensor = db.one("SELECT * FROM sensors WHERE ieee=?", (ieee,))
    if sensor:
        db.execute("UPDATE sensors SET active=0, muted_until=NULL WHERE ieee=?", (ieee,))
        db.execute("DELETE FROM alert_state WHERE sensor_id=?", (ieee,))
        db.execute("DELETE FROM discovered WHERE ieee=?", (ieee,))
        if _mqtt(request):
            _mqtt(request).remove_device(sensor["gateway_id"], ieee)
        db.add_event(utcnow(), ieee, "SENSOR_REMOVED", f"Sensore «{sensor['name']}» rimosso")
        flash(request, f"Sensore «{sensor['name']}» rimosso. Lo storico resta disponibile.")
    return _back("sensori")


# ---------- email ----------

@router.get("/email")
def email_page(request: Request):
    db = request.app.state.db
    return _page(request, "email", "email.html", smtp=settings.get(db, "smtp"),
                 recipients=settings.get(db, "recipients"),
                 pending=notifier.pending_count(db), failing=notifier.failing_count(db),
                 last_error=db.one("SELECT last_error, last_attempt_at FROM outbox "
                                   "WHERE last_error IS NOT NULL ORDER BY id DESC LIMIT 1"))


@router.post("/email")
def email_save(request: Request, host: str = Form(""), port: str = Form("587"),
               security: str = Form("starttls"), user: str = Form(""),
               password: str = Form(""), sender: str = Form(""), clear_password: str = Form("")):
    db = request.app.state.db
    smtp = settings.get(db, "smtp")
    port_n = _int(port, 1, 65535)
    if port_n is None:
        flash(request, "Porta SMTP non valida.", "alarm")
        return _back("email")
    smtp.update(host=host.strip(), port=port_n,
                security=security if security in ("starttls", "ssl", "none") else "starttls",
                user=user.strip(), sender=sender.strip())
    if clear_password:
        smtp["password"] = ""
    elif password:
        smtp["password"] = password
    settings.set(db, "smtp", smtp)
    db.add_event(utcnow(), None, "CONFIG", f"Server email: {smtp['host']}:{smtp['port']}")
    flash(request, "Impostazioni email salvate.")
    return _back("email")


@router.post("/email/destinatari")
def recipient_add(request: Request, email: str = Form("")):
    db = request.app.state.db
    email = email.strip()
    recipients = settings.get(db, "recipients")
    if not EMAIL_RE.match(email):
        flash(request, f"Indirizzo non valido: «{email}».", "alarm")
    elif email.lower() in (r.lower() for r in recipients):
        flash(request, f"{email} è già tra i destinatari.", "warn")
    else:
        settings.set(db, "recipients", recipients + [email])
        db.add_event(utcnow(), None, "CONFIG", f"Destinatario aggiunto: {email}")
        flash(request, f"{email} aggiunto ai destinatari.")
    return _back("email")


@router.post("/email/destinatari/rimuovi")
def recipient_remove(request: Request, email: str = Form("")):
    db = request.app.state.db
    recipients = settings.get(db, "recipients")
    if email in recipients:
        settings.set(db, "recipients", [r for r in recipients if r != email])
        db.add_event(utcnow(), None, "CONFIG", f"Destinatario rimosso: {email}")
        flash(request, f"{email} rimosso dai destinatari.")
    return _back("email")


@router.post("/email/prova")
def email_test(request: Request):
    db = request.app.state.db
    smtp, recipients = settings.get(db, "smtp"), settings.get(db, "recipients")
    if not smtp.get("host") or not recipients:
        flash(request, "Configura server SMTP e almeno un destinatario prima della prova.", "warn")
        return _back("email")
    try:
        refused = notifier.send_now(smtp, recipients, *notifier.render("test", None, utcnow()))
    except Exception as exc:  # noqa: BLE001 - show any SMTP error to the user
        flash(request, f"Invio fallito: {exc}", "alarm")
    else:
        if refused:
            flash(request, f"Destinatari rifiutati dal server: {notifier.refused_text(refused)}",
                  "warn")
            return _back("email")
        flash(request, f"Email di prova inviata a {', '.join(recipients)}.")
    return _back("email")


# ---------- gateway ----------

def _gateway_or_404(request: Request, gid: int):
    gw = gateways.by_id(request.app.state.gateways, gid)
    if gw is None:
        raise HTTPException(404, "Gateway sconosciuto")
    return gw


@router.get("/gateway")
def gateway_page(request: Request):
    mqtt = _mqtt(request)
    counts = {r["gateway_id"]: r["n"] for r in request.app.state.db.query(
        "SELECT gateway_id, COUNT(*) n FROM sensors WHERE active=1 GROUP BY gateway_id")}
    rows = []
    for g in request.app.state.gateways:
        bs = mqtt.states.get(g.id) if mqtt else None
        rows.append({"gw": g, "cfg": z2m_config.read_gateway(g.config),
                     "config_exists": Path(g.config).exists(),
                     "online": bool(mqtt and mqtt.connected and bs and bs.online),
                     "version": bs.version if bs else "",
                     "devices": len(bs.devices) if bs else 0,
                     "sensors": counts.get(g.id, 0)})
    return _page(request, "gateway", "gateway.html", rows=rows, mqtt=mqtt,
                 multi=len(rows) > 1)


@router.post("/gateway/{gid}")
def gateway_save(request: Request, gid: int, name: str = Form(""), ip: str = Form(""),
                 port: str = Form("6638"), adapter: str = Form("ember"),
                 channel: str = Form("11")):
    gw = _gateway_or_404(request, gid)
    db = request.app.state.db
    ip = ip.strip()
    m = IP_RE.match(ip)
    port_n, channel_n = _int(port, 1, 65535), _int(channel, 11, 26)
    if not m or any(int(x) > 255 for x in m.groups()):
        flash(request, f"Indirizzo IP non valido: «{ip}».", "alarm")
        return _back("gateway")
    if port_n is None or channel_n is None:
        flash(request, "Porta (1–65535) o canale (11–26) non validi.", "alarm")
        return _back("gateway")
    adapter = adapter if adapter in ("ember", "zstack", "deconz", "zigate") else "ember"
    name = _clean_name(name)
    if name and name != gw.name:
        try:
            gateways.rename(request.app.state.data_dir, gw.id, name)
        except (OSError, ValueError, KeyError, TypeError):
            flash(request, "Impossibile rinominare: elenco gateway (gateways.json) assente o "
                           "non valido. Esegui ./install.sh sul server.", "alarm")
            return _back("gateway")
        gw.name = name  # same object is shared with the MQTT service and monitor
    old = z2m_config.read_gateway(gw.config)
    changed = (old["ip"], old["port"], old["adapter"], old["channel"]) != \
        (ip, port_n, adapter, channel_n)
    if changed:
        try:
            z2m_config.write_gateway(gw.config, ip, port_n, adapter, channel_n)
        except OSError as exc:
            flash(request, f"Impossibile scrivere la configurazione zigbee2mqtt: {exc}", "alarm")
            return _back("gateway")
    db.add_event(utcnow(), None, "CONFIG",
                 f"Gateway {gw.name}: {ip}:{port_n}, adapter {adapter}, canale {channel_n}")
    if not changed:
        flash(request, "Gateway salvato.")
        return _back("gateway")
    mqtt = _mqtt(request)
    restarted = bool(mqtt and mqtt.restart_bridge(gw.id))
    msg = "Gateway salvato. " + ("zigbee2mqtt si sta riavviando." if restarted else
                                 "Riavvia zigbee2mqtt per applicare: "
                                 f"systemctl --user restart {gw.container}")
    if old["channel"] != channel_n and old["ip"]:
        msg += " Attenzione: con il nuovo canale i sensori vanno riabbinati."
    flash(request, msg, "ok" if restarted else "warn")
    return _back("gateway")


@router.post("/gateway/{gid}/prova")
def gateway_test(request: Request, gid: int):
    gw = _gateway_or_404(request, gid)
    cfg = z2m_config.read_gateway(gw.config)
    if not cfg["ip"]:
        flash(request, f"Imposta prima l'indirizzo IP del gateway {gw.name}.", "warn")
    elif z2m_config.test_connection(cfg["ip"], cfg["port"]):
        flash(request, f"{gw.name}: gateway raggiungibile su {cfg['ip']}:{cfg['port']}.")
    else:
        flash(request, f"{gw.name}: nessuna risposta da {cfg['ip']}:{cfg['port']}. Controlla "
                       "cavo, alimentazione e indirizzo IP del gateway.", "alarm")
    return _back("gateway")


# ---------- allarmi ----------

@router.get("/allarmi")
def alarms_page(request: Request):
    db = request.app.state.db
    return _page(request, "allarmi", "alarms.html", alarm=settings.get(db, "alarm"),
                 presets=settings.get(db, "presets"))


@router.post("/allarmi")
def alarms_save(request: Request, consecutive_samples: str = Form("2"),
                offline_minutes: str = Form("120"), battery_percent: str = Form("20"),
                fridge_min: str = Form("2"), fridge_max: str = Form("8"),
                freezer_min: str = Form("-25"), freezer_max: str = Form("-15")):
    db = request.app.state.db
    n = _int(consecutive_samples, 1, 12)
    off = _int(offline_minutes, 20, 1440)
    bat = _int(battery_percent, 5, 50)
    fridge, freezer = _thresholds(fridge_min, fridge_max), _thresholds(freezer_min, freezer_max)
    errors = [e for e in (fridge, freezer) if isinstance(e, str)]
    if n is None or off is None or bat is None:
        errors.insert(0, "Valori non validi: campioni 1–12, offline 20–1440 min, batteria 5–50 %.")
    if errors:
        flash(request, errors[0], "alarm")
        return _back("allarmi")
    settings.set(db, "alarm", {"consecutive_samples": n, "offline_minutes": off,
                               "battery_percent": bat})
    settings.set(db, "presets", {"fridge": {"min": fridge[0], "max": fridge[1]},
                                 "freezer": {"min": freezer[0], "max": freezer[1]}})
    db.add_event(utcnow(), None, "CONFIG",
                 f"Allarmi: {n} campioni, offline {off} min, batteria {bat} %")
    flash(request, "Regole di allarme salvate.")
    return _back("allarmi")


# ---------- archivio ----------

def _archive_dir(request: Request) -> Path:
    return Path(request.app.state.data_dir) / "archive"


@router.get("/archivio")
def archive_page(request: Request):
    db = request.app.state.db
    db_size = sum(p.stat().st_size for p in db.path.parent.glob(db.path.name + "*"))
    oldest = db.one("SELECT MIN(ts) ts, COUNT(*) n FROM samples")
    return _page(request, "archivio", "archive.html", files=archive.list_archives(
        _archive_dir(request)), retention=settings.get(db, "archive")["retention_days"],
        db_size=db_size, oldest=oldest)


@router.post("/archivio")
def archive_save(request: Request, retention_days: str = Form("180")):
    db = request.app.state.db
    days = _int(retention_days, 7, 3650)
    if days is None:
        flash(request, "Giorni non validi: usa un valore tra 7 e 3650.", "alarm")
    else:
        settings.set(db, "archive", {"retention_days": days})
        db.add_event(utcnow(), None, "CONFIG", f"Conservazione nel database: {days} giorni")
        flash(request, f"I campioni restano nel database per {days} giorni.")
    return _back("archivio")


@router.post("/archivio/ora")
def archive_now(request: Request):
    moved = archive.archive_old(request.app.state.db, _archive_dir(request), utcnow())
    flash(request, f"Archiviati {moved} campioni." if moved else
          "Nessun campione da archiviare: sono tutti più recenti del limite.")
    return _back("archivio")


@router.get("/archivio/{name}")
def archive_download(request: Request, name: str):
    if not re.fullmatch(r"\d{4}-\d{2}\.csv", name):
        return Response(status_code=404)
    path = _archive_dir(request) / name
    if not path.is_file():
        return Response(status_code=404)
    return FileResponse(path, media_type="text/csv", filename=f"medmonitor_{name}")


# ---------- password ----------

@router.get("/sicurezza")
def security_page(request: Request):
    return _page(request, "sicurezza", "security.html")


@router.post("/sicurezza")
def security_save(request: Request, current: str = Form(""), new: str = Form(""),
                  confirm: str = Form("")):
    db = request.app.state.db
    if not verify_password(current, settings.get(db, "admin_password_hash")):
        flash(request, "La password attuale non è corretta.", "alarm")
    elif len(new) < 6:
        flash(request, "La nuova password deve avere almeno 6 caratteri.", "alarm")
    elif new != confirm:
        flash(request, "Le due password nuove non coincidono.", "alarm")
    else:
        settings.set(db, "admin_password_hash", hash_password(new))
        db.add_event(utcnow(), None, "CONFIG", "Password di amministrazione cambiata")
        flash(request, "Password cambiata.")
    return _back("sicurezza")
