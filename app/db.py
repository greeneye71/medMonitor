"""SQLite access layer (stdlib sqlite3, WAL)."""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Rome")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sensors(
    ieee TEXT PRIMARY KEY, name TEXT NOT NULL,
    kind TEXT CHECK(kind IN ('fridge','freezer')),
    min_c REAL NOT NULL, max_c REAL NOT NULL, active INTEGER DEFAULT 1,
    muted_until TEXT, last_temp REAL, last_battery INTEGER, last_seen_at TEXT,
    created_at TEXT, gateway_id INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS samples(sensor_id TEXT, ts TEXT, temp_c REAL, battery INTEGER);
CREATE INDEX IF NOT EXISTS idx_samples ON samples(sensor_id, ts);
CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);
CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY, ts TEXT, sensor_id TEXT, type TEXT, message TEXT, value REAL);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS alert_state(
    sensor_id TEXT PRIMARY KEY, consecutive_out INTEGER DEFAULT 0,
    temp_open INTEGER DEFAULT 0, temp_since TEXT,
    offline_open INTEGER DEFAULT 0, battery_open INTEGER DEFAULT 0,
    mute_pending INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS outbox(
    id INTEGER PRIMARY KEY, created_at TEXT, subject TEXT, body_text TEXT, body_html TEXT,
    attempts INTEGER DEFAULT 0, last_error TEXT, last_attempt_at TEXT, sent_at TEXT);
CREATE TABLE IF NOT EXISTS discovered(
    ieee TEXT PRIMARY KEY, friendly_name TEXT, model TEXT, first_seen TEXT, last_temp REAL,
    last_seen TEXT, gateway_id INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS gateway_state(
    gateway_id INTEGER PRIMARY KEY, offline_open INTEGER DEFAULT 0, offline_since TEXT,
    back_at TEXT, email_sent INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse(s: str | None) -> datetime | None:
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def local(dt: datetime | str | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Format a UTC datetime (or ISO string) in Europe/Rome for display."""
    if isinstance(dt, str):
        dt = parse(dt)
    if dt is None:
        return "—"
    return dt.astimezone(LOCAL_TZ).strftime(fmt)


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        added = [("discovered", "last_seen", "TEXT"),
                 ("sensors", "gateway_id", "INTEGER NOT NULL DEFAULT 1"),
                 ("discovered", "gateway_id", "INTEGER NOT NULL DEFAULT 1"),
                 ("alert_state", "offline_email", "INTEGER DEFAULT 0")]
        for table, col, decl in added:
            cols = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        with self.lock:
            return self.conn.execute(sql, params)

    def query(self, sql: str, params=()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params=()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def add_event(self, now: datetime, sensor_id: str | None, type_: str,
                  message: str, value: float | None = None) -> None:
        self.execute("INSERT INTO events(ts,sensor_id,type,message,value) VALUES(?,?,?,?,?)",
                     (iso(now), sensor_id, type_, message, value))

    @contextmanager
    def transaction(self):
        """All-or-nothing block; other threads wait on the lock meanwhile."""
        with self.lock:
            self.conn.execute("BEGIN")
            try:
                yield
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            self.conn.execute("COMMIT")

    def close(self) -> None:
        self.conn.close()
