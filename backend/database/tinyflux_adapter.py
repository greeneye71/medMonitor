"""TinyFlux implementation of DatabaseAdapter."""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from tinyflux import TinyFlux, Point, TimeQuery, TagQuery, FieldQuery

from backend.database.adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class TinyFluxAdapter(DatabaseAdapter):
    """Database adapter using TinyFlux (CSV-based time series)."""

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._db_path = db_path
        self._db = TinyFlux(db_path)
        logger.info("TinyFlux adapter initialized: %s", db_path)

    async def write_reading(self, reading: dict[str, Any]) -> None:
        ts = reading.get("timestamp", datetime.now(timezone.utc))
        point = Point(
            time=ts,
            tags={
                "zone": reading["zone"],
                "sensor_id": reading["sensor_id"],
                "measurement": "temperature",
            },
            fields={
                "temperature": float(reading["temperature"]),
                "humidity": float(reading["humidity"]) if reading.get("humidity") is not None else 0.0,
                "battery": int(reading["battery"]) if reading.get("battery") is not None else -1,
            },
        )
        self._db.insert(point)

    async def get_readings(
        self,
        zone: str | None = None,
        sensor_id: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        time_q = TimeQuery()
        tag_q = TagQuery()

        conditions = [tag_q.measurement == "temperature"]
        if zone:
            conditions.append(tag_q.zone == zone)
        if sensor_id:
            conditions.append(tag_q.sensor_id == sensor_id)

        query = conditions[0]
        for c in conditions[1:]:
            query = query & c

        results = self._db.search(query)

        # Apply time filters
        if from_dt:
            from_aware = from_dt if from_dt.tzinfo else from_dt.replace(tzinfo=timezone.utc)
            results = [r for r in results if r.time >= from_aware]
        if to_dt:
            to_aware = to_dt if to_dt.tzinfo else to_dt.replace(tzinfo=timezone.utc)
            results = [r for r in results if r.time <= to_aware]

        # Sort by time descending, apply limit
        results.sort(key=lambda r: r.time, reverse=True)
        results = results[:limit]

        return [self._point_to_reading(r) for r in results]

    async def get_latest(self) -> list[dict[str, Any]]:
        tag_q = TagQuery()
        results = self._db.search(tag_q.measurement == "temperature")

        # Group by sensor_id, keep latest
        latest: dict[str, Point] = {}
        for r in results:
            sid = r.tags.get("sensor_id", "")
            if sid not in latest or r.time > latest[sid].time:
                latest[sid] = r

        return [self._point_to_reading(p) for p in latest.values()]

    async def write_alert(self, alert: dict[str, Any]) -> None:
        ts = alert.get("timestamp", datetime.now(timezone.utc))
        point = Point(
            time=ts,
            tags={
                "zone": alert["zone"],
                "sensor_id": alert["sensor_id"],
                "level": alert["level"],
                "measurement": "alert",
                "message": str(alert.get("message", "")),
            },
            fields={
                "temperature": float(alert["temperature"]),
                "threshold_min": float(alert["threshold_min"]),
                "threshold_max": float(alert["threshold_max"]),
            },
        )
        self._db.insert(point)

    async def get_alerts(
        self,
        zone: str | None = None,
        level: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        tag_q = TagQuery()

        conditions = [tag_q.measurement == "alert"]
        if zone:
            conditions.append(tag_q.zone == zone)
        if level:
            conditions.append(tag_q.level == level)

        query = conditions[0]
        for c in conditions[1:]:
            query = query & c

        results = self._db.search(query)

        if from_dt:
            from_aware = from_dt if from_dt.tzinfo else from_dt.replace(tzinfo=timezone.utc)
            results = [r for r in results if r.time >= from_aware]
        if to_dt:
            to_aware = to_dt if to_dt.tzinfo else to_dt.replace(tzinfo=timezone.utc)
            results = [r for r in results if r.time <= to_aware]

        results.sort(key=lambda r: r.time, reverse=True)
        results = results[:limit]

        return [self._point_to_alert(r) for r in results]

    async def delete_demo_data(self) -> int:
        tag_q = TagQuery()
        removed = self._db.remove(tag_q.sensor_id.test(lambda v: v.startswith("0xDEMO")))
        count = removed if isinstance(removed, int) else len(removed)
        logger.info("Deleted %d demo records from TinyFlux", count)
        return count

    async def close(self) -> None:
        self._db.close()
        logger.info("TinyFlux adapter closed")

    @staticmethod
    def _point_to_reading(point: Point) -> dict[str, Any]:
        battery = point.fields.get("battery", -1)
        return {
            "zone": point.tags.get("zone", ""),
            "sensor_id": point.tags.get("sensor_id", ""),
            "temperature": point.fields.get("temperature", 0.0),
            "humidity": point.fields.get("humidity", 0.0) or None,
            "battery": battery if battery >= 0 else None,
            "timestamp": point.time,
        }

    @staticmethod
    def _point_to_alert(point: Point) -> dict[str, Any]:
        return {
            "zone": point.tags.get("zone", ""),
            "sensor_id": point.tags.get("sensor_id", ""),
            "level": point.tags.get("level", ""),
            "temperature": point.fields.get("temperature", 0.0),
            "threshold_min": point.fields.get("threshold_min", 0.0),
            "threshold_max": point.fields.get("threshold_max", 0.0),
            "message": point.tags.get("message", ""),
            "timestamp": point.time,
        }
