"""Move samples older than retention to monthly CSV files (data/archive/AAAA-MM.csv)."""
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

from app import settings
from app.db import LOCAL_TZ, Database, iso, parse

HEADER = ["timestamp", "sensor_id", "sensor_name", "temp_c", "battery"]


def archive_old(db: Database, archive_dir: str | Path, now: datetime) -> int:
    """Append old samples to CSV (fsync), then delete them from the DB. Returns rows moved."""
    days = int(settings.get(db, "archive")["retention_days"])
    cutoff = iso(now - timedelta(days=days))
    rows = db.query(
        "SELECT s.ts, s.sensor_id, COALESCE(n.name, s.sensor_id) AS name, s.temp_c, s.battery "
        "FROM samples s LEFT JOIN sensors n ON n.ieee = s.sensor_id "
        "WHERE s.ts < ? ORDER BY s.ts", (cutoff,))
    if not rows:
        return 0
    archive_dir = Path(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    by_month: dict[str, list] = {}
    for r in rows:
        ts = parse(r["ts"]).astimezone(LOCAL_TZ)
        by_month.setdefault(ts.strftime("%Y-%m"), []).append(
            [ts.isoformat(), r["sensor_id"], r["name"], r["temp_c"],
             "" if r["battery"] is None else r["battery"]])

    for month, lines in by_month.items():
        path = archive_dir / f"{month}.csv"
        new = not path.exists() or path.stat().st_size == 0
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(HEADER)
            w.writerows(lines)
            f.flush()
            os.fsync(f.fileno())

    db.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
    db.add_event(now, None, "ARCHIVE",
                 f"Archiviati {len(rows)} campioni in {', '.join(sorted(by_month))}")
    return len(rows)


def list_archives(archive_dir: str | Path) -> list[dict]:
    d = Path(archive_dir)
    if not d.is_dir():
        return []
    return [{"name": p.name, "size": p.stat().st_size}
            for p in sorted(d.glob("*.csv"), reverse=True)]
