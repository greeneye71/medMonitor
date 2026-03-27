"""Archive service — export readings/alerts to CSV, then purge from DB."""

import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from backend.paths import data_file
    ARCHIVE_DIR = data_file("archive")
except (ImportError, AttributeError):
    ARCHIVE_DIR = Path("data/archive")


class ArchiveService:
    def __init__(self, db, config_service):
        self._db = db
        self._config = config_service

    async def run(self) -> dict:
        cfg = self._config.get_config()
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=cfg.archive_after_days)
        logger.info("Archive: cutoff=%s", cutoff.isoformat())

        # get_readings(zone, sensor_id, from_dt, to_dt, limit)
        readings = await self._db.get_readings(
            zone=None, sensor_id=None, from_dt=None, to_dt=cutoff, limit=1_000_000
        )
        # get_alerts(zone, level, from_dt, to_dt, limit)
        alerts = await self._db.get_alerts(to_dt=cutoff, limit=1_000_000)

        rows_archived = 0
        files_written = []

        def _month_key(ts_val) -> str:
            if isinstance(ts_val, str):
                return ts_val[:7]
            # datetime object
            return ts_val.strftime("%Y-%m")

        readings_by_month = defaultdict(list)
        for r in readings:
            readings_by_month[_month_key(r["timestamp"])].append(r)

        alerts_by_month = defaultdict(list)
        for a in alerts:
            alerts_by_month[_month_key(a["timestamp"])].append(a)

        for month in sorted(set(readings_by_month) | set(alerts_by_month)):
            month_dir = Path(ARCHIVE_DIR) / month
            month_dir.mkdir(parents=True, exist_ok=True)

            if readings_by_month[month]:
                path = month_dir / "readings.csv"
                _write_csv(path, readings_by_month[month],
                           ["timestamp", "zone", "sensor_id", "temperature", "humidity", "battery"])
                files_written.append(str(path))
                rows_archived += len(readings_by_month[month])

            if alerts_by_month[month]:
                path = month_dir / "alerts.csv"
                _write_csv(path, alerts_by_month[month],
                           ["timestamp", "zone", "sensor_id", "temperature", "level", "message", "resolved"])
                files_written.append(str(path))
                rows_archived += len(alerts_by_month[month])

        if readings:
            await self._db.delete_readings_before(cutoff)
        if alerts:
            await self._db.delete_alerts_before(cutoff)

        log_path = Path(ARCHIVE_DIR) / "archive_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_data = {
            "last_run": datetime.now(tz=timezone.utc).isoformat(),
            "last_rows_archived": rows_archived,
            "files": files_written,
        }
        log_path.write_text(json.dumps(log_data, indent=2), encoding="utf-8")
        logger.info("Archive complete: %d rows", rows_archived)
        return {"status": "completed", "rows_archived": rows_archived, "files_written": files_written}

    def get_status(self) -> dict:
        log_path = Path(ARCHIVE_DIR) / "archive_log.json"
        base = {"last_run": None, "last_rows_archived": 0,
                "archive_dir": str(ARCHIVE_DIR), "files": []}
        if log_path.exists():
            try:
                return {**base, **json.loads(log_path.read_text(encoding="utf-8"))}
            except Exception:
                pass
        return base


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
