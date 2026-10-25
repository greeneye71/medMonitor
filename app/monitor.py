"""Sampling and alarm evaluation. Pure logic over the DB; `now` is always explicit."""
from datetime import datetime, timedelta

from app import settings
from app.db import Database, iso, parse
from app.notifier import notify


def _duration(td: timedelta) -> str:
    minutes = int(td.total_seconds() // 60)
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if h else f"{m} min"


def is_offline(sensor: dict, now: datetime, offline_minutes: int,
               back_at: datetime | None = None) -> bool:
    """No data for `offline_minutes`; `back_at` (gateway reconnection) restarts the clock."""
    seen = parse(sensor["last_seen_at"])
    if back_at is not None and (seen is None or back_at > seen):
        seen = back_at
    return seen is None or now - seen > timedelta(minutes=offline_minutes)


def take_samples(db: Database, now: datetime) -> dict[str, float]:
    """Write one sample per online active sensor. Returns {ieee: temp} of sampled sensors.

    No gateway `back_at` grace here: a reading older than `offline_minutes` is stale and
    must not become a sample, even while the offline alarm waits for the sensor to speak.
    """
    offline_min = int(settings.get(db, "alarm")["offline_minutes"])
    sampled = {}
    for s in db.query("SELECT * FROM sensors WHERE active=1"):
        if is_offline(s, now, offline_min) or s["last_temp"] is None:
            continue
        db.execute("INSERT INTO samples(sensor_id,ts,temp_c,battery) VALUES(?,?,?,?)",
                   (s["ieee"], iso(now), s["last_temp"], s["last_battery"]))
        sampled[s["ieee"]] = s["last_temp"]
    return sampled


def _state(db: Database, ieee: str) -> dict:
    db.execute("INSERT OR IGNORE INTO alert_state(sensor_id) VALUES(?)", (ieee,))
    return db.one("SELECT * FROM alert_state WHERE sensor_id=?", (ieee,))


def _save_state(db: Database, st: dict) -> None:
    db.execute("UPDATE alert_state SET consecutive_out=?, temp_open=?, temp_since=?, "
               "offline_open=?, battery_open=?, mute_pending=?, offline_email=? "
               "WHERE sensor_id=?",
               (st["consecutive_out"], st["temp_open"], st["temp_since"], st["offline_open"],
                st["battery_open"], st["mute_pending"], st["offline_email"], st["sensor_id"]))


def _muted(s: dict, now: datetime) -> bool:
    """Emails suppressed: switched off for the sensor or paused until `muted_until`."""
    if not s.get("notify", 1):
        return True
    until = parse(s["muted_until"])
    return until is not None and until > now


def _gateway_state(db: Database, gid: int) -> dict:
    db.execute("INSERT OR IGNORE INTO gateway_state(gateway_id) VALUES(?)", (gid,))
    return db.one("SELECT * FROM gateway_state WHERE gateway_id=?", (gid,))


def evaluate_gateways(db: Database, now: datetime, gateways, states, connected: bool,
                      started_at: datetime | None) -> set[int]:
    """Open/close the "gateway non raggiungibile" alarm. Returns ids whose bridge is not online.

    Without a broker connection we know nothing about the bridges: no alarm changes.
    """
    down = {g.id for g in gateways if g.id in states and not states[g.id].online}
    if not connected:
        return down
    offline_min = int(settings.get(db, "alarm")["offline_minutes"])
    for g in gateways:
        bs = states.get(g.id)
        if bs is None:
            continue
        with db.transaction():
            gst = _gateway_state(db, g.id)
            if not bs.online and not gst["offline_open"]:
                since = bs.offline_since or started_at
                if since is None or now - since <= timedelta(minutes=offline_min):
                    continue
                sensors = [s for s in db.query(
                    "SELECT * FROM sensors WHERE active=1 AND gateway_id=? ORDER BY name",
                    (g.id,)) if not _muted(s, now)]
                if not sensors:
                    continue
                db.add_event(now, None, "GATEWAY_OFFLINE_OPEN",
                             f"{g.name}: gateway non raggiungibile da oltre {offline_min} min",
                             gateway_id=g.id)
                notify(db, now, "gateway_offline_open", gateway=g,
                       sensors=[s["name"] for s in sensors], minutes=offline_min)
                db.execute("UPDATE gateway_state SET offline_open=1, offline_since=? "
                           "WHERE gateway_id=?", (iso(since), g.id))
            elif bs.online and gst["offline_open"]:
                # The alarm only opens together with its email: the closing one always follows.
                db.add_event(now, None, "GATEWAY_OFFLINE_CLOSE",
                             f"{g.name}: gateway di nuovo raggiungibile", gateway_id=g.id)
                notify(db, now, "gateway_offline_close", gateway=g, minutes=offline_min)
                db.execute("UPDATE gateway_state SET offline_open=0, offline_since=NULL "
                           "WHERE gateway_id=?", (g.id,))
    return down


def evaluate(db: Database, now: datetime, sampled: dict[str, float],
             gateways_down: set[int] = frozenset(),
             back_at: dict[int, datetime] | None = None,
             ambienti: dict[int, str] | None = None) -> None:
    """Update alarm state for every active sensor; log events and queue emails.

    `ambienti` maps gateway id to name; emails name the ambiente only when it is given.
    """
    alarm = settings.get(db, "alarm")
    back_at = back_at or {}
    ambienti = ambienti or {}
    for s in db.query("SELECT * FROM sensors WHERE active=1"):
        with db.transaction():      # event, email and state change together or not at all
            _evaluate_sensor(db, now, sampled, s, alarm, s["gateway_id"] in gateways_down,
                             back_at.get(s["gateway_id"]), ambienti.get(s["gateway_id"]))


def _evaluate_sensor(db: Database, now: datetime, sampled: dict[str, float], s: dict,
                     alarm: dict, gateway_down: bool = False,
                     back_at: datetime | None = None, ambiente: str | None = None) -> None:
    n_required = int(alarm["consecutive_samples"])
    offline_min = int(alarm["offline_minutes"])
    batt_low = int(alarm["battery_percent"])
    ieee = s["ieee"]
    st = _state(db, ieee)
    muted = _muted(s, now)

    sent = set()

    def send(kind, **ctx):
        if muted:
            st["mute_pending"] = 1
        else:
            notify(db, now, kind, s, ambiente, **ctx)
            sent.add(kind)

    # OFFLINE
    # The gateway alarm covers sensors behind a bridge that is down: event only, no email.
    # "Di nuovo online" goes out only if the sensor's own offline email did.
    def send_offline_open():
        if gateway_down:
            return
        send("offline_open", minutes=offline_min)
        if "offline_open" in sent:
            st["offline_email"] = 1

    offline = is_offline(s, now, offline_min, back_at)
    if offline and not st["offline_open"]:
        st["offline_open"] = 1
        db.add_event(now, ieee, "OFFLINE_OPEN",
                     f"{s['name']}: nessun dato da oltre {offline_min} min")
        send_offline_open()
    elif not offline and st["offline_open"]:
        st["offline_open"] = 0
        db.add_event(now, ieee, "OFFLINE_CLOSE", f"{s['name']}: di nuovo online")
        if st["offline_email"]:
            send("offline_close")
        st["offline_email"] = 0

    # TEMP (evaluated only on a new sample; offline leaves the counter untouched)
    if ieee in sampled:
        temp = sampled[ieee]
        if temp < s["min_c"] or temp > s["max_c"]:
            st["consecutive_out"] += 1
            if st["consecutive_out"] == 1:
                st["temp_since"] = iso(now)
            if st["consecutive_out"] >= n_required and not st["temp_open"]:
                st["temp_open"] = 1
                db.add_event(now, ieee, "TEMP_OPEN",
                             f"{s['name']}: {temp:.1f} °C fuori soglia "
                             f"({s['min_c']:g}…{s['max_c']:g} °C)", temp)
                send("temp_open", value=temp, since=st["temp_since"])
        else:
            if st["temp_open"]:
                dur = _duration(now - (parse(st["temp_since"]) or now))
                st["temp_open"] = 0
                db.add_event(now, ieee, "TEMP_CLOSE",
                             f"{s['name']}: temperatura rientrata ({temp:.1f} °C, "
                             f"durata {dur})", temp)
                send("temp_close", value=temp, duration=dur)
            st["consecutive_out"] = 0
            st["temp_since"] = None

    # BATTERY (hysteresis +5%, close without email)
    batt = s["last_battery"]
    if batt is not None:
        if batt < batt_low and not st["battery_open"]:
            st["battery_open"] = 1
            db.add_event(now, ieee, "BATTERY_OPEN", f"{s['name']}: batteria al {batt}%", batt)
            send("battery_open")
        elif batt >= batt_low + 5 and st["battery_open"]:
            st["battery_open"] = 0
            db.add_event(now, ieee, "BATTERY_CLOSE", f"{s['name']}: batteria al {batt}%",
                         batt)

    # Mute expired after suppressed emails: re-send the opening email for alerts that are
    # still open after this cycle's evaluation and were not just notified.
    if st["mute_pending"] and not muted:
        st["mute_pending"] = 0
        if st["temp_open"] and "temp_open" not in sent:
            notify(db, now, "temp_open", s, ambiente, value=s["last_temp"], since=st["temp_since"])
        if st["offline_open"] and "offline_open" not in sent and not gateway_down:
            notify(db, now, "offline_open", s, ambiente, minutes=offline_min)
            st["offline_email"] = 1
        if st["battery_open"] and "battery_open" not in sent:
            notify(db, now, "battery_open", s, ambiente)

    _save_state(db, st)


def run_cycle(db: Database, now: datetime, gateways=None, states=None, connected: bool = True,
              started_at: datetime | None = None) -> None:
    """One sampling tick. Without `gateways` (no MQTT service) only sensors are evaluated."""
    sampled = take_samples(db, now)
    if gateways is None:
        evaluate(db, now, sampled)
        return
    down = evaluate_gateways(db, now, gateways, states or {}, connected, started_at)
    back_at = {r["gateway_id"]: parse(r["back_at"])
               for r in db.query("SELECT gateway_id, back_at FROM gateway_state")}
    ambienti = {g.id: g.name for g in gateways} if len(gateways) > 1 else {}
    evaluate(db, now, sampled, down, back_at, ambienti)


def sensor_status(sensor: dict, st: dict | None, now: datetime, offline_minutes: int,
                  back_at: datetime | None = None) -> str:
    """UI status: offline | alarm | out | battery | ok. `back_at` as in `is_offline`."""
    if is_offline(sensor, now, offline_minutes, back_at):
        return "offline"
    st = st or {}
    if st.get("temp_open"):
        return "alarm"
    t = sensor["last_temp"]
    if t is not None and (t < sensor["min_c"] or t > sensor["max_c"]):
        return "out"
    if st.get("battery_open"):
        return "battery"
    return "ok"
