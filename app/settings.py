"""Settings stored as JSON in the `settings` table, with defaults."""
import copy
import json

from app.db import Database

DEFAULTS = {
    "smtp": {"host": "", "port": 587, "security": "starttls", "user": "", "password": "", "sender": ""},
    "recipients": [],
    "alarm": {"consecutive_samples": 2, "offline_minutes": 120, "battery_percent": 20},
    "presets": {"fridge": {"min": 2, "max": 8}, "freezer": {"min": -25, "max": -15}},
    "archive": {"retention_days": 180},
    "admin_password_hash": "",
}


def get(db: Database, key: str):
    row = db.one("SELECT value FROM settings WHERE key=?", (key,))
    default = copy.deepcopy(DEFAULTS.get(key))
    if row is None:
        return default
    value = json.loads(row["value"])
    if isinstance(default, dict) and isinstance(value, dict):
        default.update(value)
        return default
    return value


def set(db: Database, key: str, value) -> None:  # noqa: A001
    db.execute("INSERT INTO settings(key,value) VALUES(?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))
