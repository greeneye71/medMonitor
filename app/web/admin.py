"""Password-protected settings pages (/impostazioni/...).

Handlers are plain `def` (run in the threadpool) because send_now uses asyncio.run.
"""
import re
import time
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from app import archive, notifier, settings, z2m_config
from app.auth import hash_password, require_admin, verify_password
from app.db import iso, utcnow
from app.web import KIND_LABEL, flash, render

router = APIRouter(prefix="/impostazioni", dependencies=[Depends(require_admin)])

TABS = [("sensori", "Sensori"), ("email", "Email"), ("gateway", "Gateway"),
        ("allarmi", "Allarmi"), ("archivio", "Archivio"), ("sicurezza", "Password")]
MUTE_HOURS = (1, 4, 24)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IP_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")


def _back(tab: str) -> RedirectResponse:
    return RedirectResponse(f"/impostazioni/{tab}", status_code=303)


def _float(value: str) -> float | None:
    try:
        return float(value.strip().replace(",", ".").replace("−", "-"))
    except (ValueError, AttributeError):
        return None


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


def _pairing_left(request: Request) -> int:
    mqtt = _mqtt(request)
    return max(0, int(mqtt.state.permit_join_until - time.time())) if mqtt else 0


@router.get("/sensori")
def sensors_page(request: Request):
    db = request.app.state.db
    return _page(request, "sensori", "sensors.html",
                 sensors=db.query("SELECT * FROM sensors WHERE active=1 "
                                  "ORDER BY name COLLATE NOCASE"),
                 discovered=_discovered(request), presets=settings.get(db, "presets"),
                 pairing_left=_pairing_left(request), mute_hours=MUTE_HOURS,
                 now=utcnow())


@router.get("/sensori/rilevati")
def discovered_partial(request: Request):
    db = request.app.state.db
    return render(request, "settings/_discovered.html", discovered=_discovered(request),
                  presets=settings.get(db, "presets"), pairing_left=_pairing_left(request))


@router.post("/sensori/abbina")
def pair(request: Request):
    mqtt = _mqtt(request)
    if mqtt and mqtt.permit_join(120):
        mqtt.state.permit_join_until = time.time() + 120
        flash(request, "Abbinamento aperto per 2 minuti: premi il tasto sul sensore.")
    else:
        flash(request, "Gateway non raggiungibile: impossibile avviare l'abbinamento.", "alarm")
    return _back("sensori")


@router.post("/sensori/aggiungi")
def add_sensor(request: Request, ieee: str = Form(...), name: str = Form(""),
               kind: str = Form("fridge"), min_c: str = Form(""), max_c: str = Form("")):
    db = request.app.state.db
    name, kind = name.strip(), kind if kind in KIND_LABEL else "fridge"
    found = db.one("SELECT * FROM discovered WHERE ieee=?", (ieee,))
    if not found:
        flash(request, "Sensore non trovato tra quelli rilevati.", "alarm")
        return _back("sensori")
    th = _thresholds(min_c, max_c)
    if isinstance(th, str) or not name:
        flash(request, th if isinstance(th, str) else "Inserisci un nome per il sensore.", "alarm")
        return _back("sensori")
    now = utcnow()
    seen = iso(now) if found["last_temp"] is not None else None
    db.execute(
        "INSERT INTO sensors(ieee,name,kind,min_c,max_c,active,last_temp,last_seen_at,created_at) "
        "VALUES(?,?,?,?,?,1,?,?,?) ON CONFLICT(ieee) DO UPDATE SET name=excluded.name, "
        "kind=excluded.kind, min_c=excluded.min_c, max_c=excluded.max_c, active=1, "
        "muted_until=NULL, last_temp=COALESCE(excluded.last_temp, sensors.last_temp), "
        "last_seen_at=COALESCE(excluded.last_seen_at, sensors.last_seen_at)",
        (ieee, name, kind, th[0], th[1], found["last_temp"], seen, iso(now)))
    db.add_event(now, ieee, "SENSOR_ADDED", f"Sensore «{name}» aggiunto ({th[0]} … {th[1]} °C)")
    flash(request, f"Sensore «{name}» aggiunto.")
    return _back("sensori")


@router.post("/sensori/{ieee}/modifica")
def edit_sensor(request: Request, ieee: str, name: str = Form(""), kind: str = Form("fridge"),
                min_c: str = Form(""), max_c: str = Form("")):
    db = request.app.state.db
    sensor = db.one("SELECT * FROM sensors WHERE ieee=? AND active=1", (ieee,))
    th = _thresholds(min_c, max_c)
    if not sensor:
        flash(request, "Sensore non trovato.", "alarm")
    elif isinstance(th, str) or not name.strip():
        flash(request, th if isinstance(th, str) else "Il nome non può essere vuoto.", "alarm")
    else:
        kind = kind if kind in KIND_LABEL else sensor["kind"]
        db.execute("UPDATE sensors SET name=?, kind=?, min_c=?, max_c=? WHERE ieee=?",
                   (name.strip(), kind, th[0], th[1], ieee))
        db.add_event(utcnow(), ieee, "CONFIG",
                     f"Sensore «{name.strip()}»: soglie {th[0]} … {th[1]} °C")
        flash(request, f"Sensore «{name.strip()}» salvato.")
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
            _mqtt(request).remove_device(ieee)
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
               password: str = Form(""), sender: str = Form("")):
    db = request.app.state.db
    smtp = settings.get(db, "smtp")
    port_n = _int(port, 1, 65535)
    if port_n is None:
        flash(request, "Porta SMTP non valida.", "alarm")
        return _back("email")
    smtp.update(host=host.strip(), port=port_n,
                security=security if security in ("starttls", "ssl", "none") else "starttls",
                user=user.strip(), sender=sender.strip())
    if password:
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
        notifier.send_now(smtp, recipients, *notifier.render("test", None, utcnow()))
    except Exception as exc:  # noqa: BLE001 - show any SMTP error to the user
        flash(request, f"Invio fallito: {exc}", "alarm")
    else:
        flash(request, f"Email di prova inviata a {', '.join(recipients)}.")
    return _back("email")


# ---------- gateway ----------

@router.get("/gateway")
def gateway_page(request: Request):
    mqtt = _mqtt(request)
    path = request.app.state.z2m_path
    return _page(request, "gateway", "gateway.html", gw=z2m_config.read_gateway(path),
                 config_exists=Path(path).exists(), mqtt=mqtt,
                 devices=len(mqtt.state.devices) if mqtt else 0,
                 frontend_url=f"http://{request.url.hostname}:8080")


@router.post("/gateway")
def gateway_save(request: Request, ip: str = Form(""), port: str = Form("6638"),
                 adapter: str = Form("ember"), channel: str = Form("11")):
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
    path = request.app.state.z2m_path
    old = z2m_config.read_gateway(path)
    try:
        z2m_config.write_gateway(path, ip, port_n, adapter, channel_n)
    except OSError as exc:
        flash(request, f"Impossibile scrivere la configurazione zigbee2mqtt: {exc}", "alarm")
        return _back("gateway")
    db.add_event(utcnow(), None, "CONFIG",
                 f"Gateway: {ip}:{port_n}, adapter {adapter}, canale {channel_n}")
    mqtt = _mqtt(request)
    restarted = bool(mqtt and mqtt.restart_bridge())
    msg = "Gateway salvato. " + ("zigbee2mqtt si sta riavviando." if restarted else
                                 "Riavvia zigbee2mqtt per applicare: "
                                 "systemctl --user restart zigbee2mqtt")
    if old["channel"] != channel_n and old["ip"]:
        msg += " Attenzione: con il nuovo canale i sensori vanno riabbinati."
    flash(request, msg, "ok" if restarted else "warn")
    return _back("gateway")


@router.post("/gateway/prova")
def gateway_test(request: Request):
    gw = z2m_config.read_gateway(request.app.state.z2m_path)
    if not gw["ip"]:
        flash(request, "Imposta prima l'indirizzo IP del gateway.", "warn")
    elif z2m_config.test_connection(gw["ip"], gw["port"]):
        flash(request, f"Gateway raggiungibile su {gw['ip']}:{gw['port']}.")
    else:
        flash(request, f"Nessuna risposta da {gw['ip']}:{gw['port']}. Controlla cavo, "
                       "alimentazione e indirizzo IP del gateway.", "alarm")
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
