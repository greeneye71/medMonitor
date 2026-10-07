"""Sampling and alarm evaluation. Pure logic over the DB; `now` is always explicit."""
from datetime import datetime, timedelta

from app import settings
from app.db import Database, iso, parse
from app.notifier import notify


def _duration(td: timedelta) -> str:
    minutes = int(td.total_seconds() // 60)
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if h else f"{m} min"


def is_offline(sensor: dict, now: datetime, offline_minutes: int) -> bool:
    seen = parse(sensor["last_seen_at"])
    return seen is None or now - seen > timedelta(minutes=offline_minutes)


def take_samples(db: Database, now: datetime) -> dict[str, float]:
    """Write one sample per online active sensor. Returns {ieee: temp} of sampled sensors."""
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
               "offline_open=?, battery_open=?, mute_pending=? WHERE sensor_id=?",
               (st["consecutive_out"], st["temp_open"], st["temp_since"], st["offline_open"],
                st["battery_open"], st["mute_pending"], st["sensor_id"]))


def evaluate(db: Database, now: datetime, sampled: dict[str, float]) -> None:
    """Update alarm state for every active sensor; log events and queue emails."""
    alarm = settings.get(db, "alarm")
    n_required = int(alarm["consecutive_samples"])
    offline_min = int(alarm["offline_minutes"])
    batt_low = int(alarm["battery_percent"])

    for s in db.query("SELECT * FROM sensors WHERE active=1"):
        ieee = s["ieee"]
        st = _state(db, ieee)
        muted_until = parse(s["muted_until"])
        muted = muted_until is not None and muted_until > now

        def send(kind, **ctx):
            if muted:
                st["mute_pending"] = 1
            else:
                notify(db, now, kind, s, **ctx)

        # Mute expired after suppressed emails: re-send opening email for alerts still open.
        if st["mute_pending"] and not muted:
            st["mute_pending"] = 0
            if st["temp_open"]:
                notify(db, now, "temp_open", s, value=s["last_temp"], since=st["temp_since"])
            if st["offline_open"]:
                notify(db, now, "offline_open", s, minutes=offline_min)
            if st["battery_open"]:
                notify(db, now, "battery_open", s)

        # OFFLINE
        offline = is_offline(s, now, offline_min)
        if offline and not st["offline_open"]:
            st["offline_open"] = 1
            db.add_event(now, ieee, "OFFLINE_OPEN",
                         f"{s['name']}: nessun dato da oltre {offline_min} min")
            send("offline_open", minutes=offline_min)
        elif not offline and st["offline_open"]:
            st["offline_open"] = 0
            db.add_event(now, ieee, "OFFLINE_CLOSE", f"{s['name']}: di nuovo online")
            send("offline_close")

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

        _save_state(db, st)


def run_cycle(db: Database, now: datetime) -> None:
    evaluate(db, now, take_samples(db, now))


def sensor_status(sensor: dict, st: dict | None, now: datetime, offline_minutes: int) -> str:
    """UI status: offline | alarm | out | battery | ok."""
    if is_offline(sensor, now, offline_minutes):
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
