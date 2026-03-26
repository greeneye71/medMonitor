"""TimescaleDB (asyncpg) implementation of DatabaseAdapter."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg

from backend.database.adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class TimescaleAdapter(DatabaseAdapter):
    """Database adapter using TimescaleDB via asyncpg."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None
        self._pool_lock = asyncio.Lock()

    async def _ensure_pool(self) -> asyncpg.Pool:
        # Fast path: pool already created
        if self._pool is not None:
            return self._pool
        # Slow path: acquire lock, double-check, then create
        async with self._pool_lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
                logger.info("TimescaleDB connection pool created")
        return self._pool

    async def write_reading(self, reading: dict[str, Any]) -> None:
        pool = await self._ensure_pool()
        ts = reading.get("timestamp", datetime.now(timezone.utc))
        await pool.execute(
            """
            INSERT INTO temperature_readings
                (zone, sensor_id, temperature, humidity, battery, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            reading["zone"],
            reading["sensor_id"],
            float(reading["temperature"]),
            float(reading["humidity"]) if reading.get("humidity") is not None else None,
            int(reading["battery"]) if reading.get("battery") is not None else None,
            ts,
        )

    async def get_readings(
        self,
        zone: str | None = None,
        sensor_id: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        pool = await self._ensure_pool()
        conditions = []
        params: list[Any] = []
        idx = 1

        if zone:
            conditions.append(f"zone = ${idx}")
            params.append(zone)
            idx += 1
        if sensor_id:
            conditions.append(f"sensor_id = ${idx}")
            params.append(sensor_id)
            idx += 1
        if from_dt:
            conditions.append(f"timestamp >= ${idx}")
            params.append(from_dt)
            idx += 1
        if to_dt:
            conditions.append(f"timestamp <= ${idx}")
            params.append(to_dt)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        limit_clause = ""
        if limit is not None:
            params.append(limit)
            limit_clause = f"LIMIT ${idx}"

        query = f"""
            SELECT zone, sensor_id, temperature, humidity, battery, timestamp
            FROM temperature_readings
            {where}
            ORDER BY timestamp DESC
            {limit_clause}
        """

        rows = await pool.fetch(query, *params)
        return [self._row_to_reading(r) for r in rows]

    async def get_latest(self) -> list[dict[str, Any]]:
        pool = await self._ensure_pool()
        rows = await pool.fetch("""
            SELECT DISTINCT ON (sensor_id)
                zone, sensor_id, temperature, humidity, battery, timestamp
            FROM temperature_readings
            ORDER BY sensor_id, timestamp DESC
        """)
        return [self._row_to_reading(r) for r in rows]

    async def write_alert(self, alert: dict[str, Any]) -> None:
        pool = await self._ensure_pool()
        ts = alert.get("timestamp", datetime.now(timezone.utc))
        alert_id = alert.get("id") or str(uuid.uuid4())[:8]
        await pool.execute(
            """
            INSERT INTO alerts
                (id, zone, sensor_id, temperature, level, threshold_min,
                 threshold_max, message, timestamp, resolved)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            alert_id,
            alert["zone"],
            alert["sensor_id"],
            float(alert["temperature"]),
            alert["level"],
            float(alert["threshold_min"]),
            float(alert["threshold_max"]),
            alert.get("message", ""),
            ts,
            alert.get("resolved", False),
        )

    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved in TimescaleDB."""
        pool = await self._ensure_pool()
        result = await pool.execute(
            "UPDATE alerts SET resolved = TRUE WHERE id = $1",
            alert_id,
        )
        # asyncpg returns "UPDATE N" — N>0 means a row was updated
        updated = int(result.split()[-1]) if result else 0
        return updated > 0

    async def get_alerts(
        self,
        zone: str | None = None,
        level: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        pool = await self._ensure_pool()
        conditions = []
        params: list[Any] = []
        idx = 1

        if zone:
            conditions.append(f"zone = ${idx}")
            params.append(zone)
            idx += 1
        if level:
            conditions.append(f"level = ${idx}")
            params.append(level)
            idx += 1
        if from_dt:
            conditions.append(f"timestamp >= ${idx}")
            params.append(from_dt)
            idx += 1
        if to_dt:
            conditions.append(f"timestamp <= ${idx}")
            params.append(to_dt)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        limit_clause = ""
        if limit is not None:
            params.append(limit)
            limit_clause = f"LIMIT ${idx}"

        query = f"""
            SELECT id, zone, sensor_id, temperature, level, threshold_min,
                   threshold_max, message, timestamp, resolved
            FROM alerts
            {where}
            ORDER BY timestamp DESC
            {limit_clause}
        """

        rows = await pool.fetch(query, *params)
        return [self._row_to_alert(r) for r in rows]

    async def delete_demo_data(self) -> int:
        pool = await self._ensure_pool()
        result_readings = await pool.execute(
            "DELETE FROM temperature_readings WHERE sensor_id LIKE '0xDEMO%'"
        )
        result_alerts = await pool.execute(
            "DELETE FROM alerts WHERE sensor_id LIKE '0xDEMO%'"
        )
        # asyncpg.execute() returns command tag like "DELETE 5"
        count_readings = int(result_readings.split()[-1]) if result_readings else 0
        count_alerts = int(result_alerts.split()[-1]) if result_alerts else 0
        total = count_readings + count_alerts
        logger.info("Deleted %d demo records from TimescaleDB (%d readings, %d alerts)",
                     total, count_readings, count_alerts)
        return total

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("TimescaleDB connection pool closed")

    @staticmethod
    def _row_to_reading(row: asyncpg.Record) -> dict[str, Any]:
        return {
            "zone": row["zone"],
            "sensor_id": row["sensor_id"],
            "temperature": float(row["temperature"]),
            "humidity": float(row["humidity"]) if row["humidity"] is not None else None,
            "battery": int(row["battery"]) if row["battery"] is not None else None,
            "timestamp": row["timestamp"],
        }

    @staticmethod
    def _row_to_alert(row: asyncpg.Record) -> dict[str, Any]:
        keys = row.keys()
        return {
            "id": row["id"] if "id" in keys else "",
            "zone": row["zone"],
            "sensor_id": row["sensor_id"],
            "temperature": float(row["temperature"]),
            "level": row["level"],
            "threshold_min": float(row["threshold_min"]),
            "threshold_max": float(row["threshold_max"]),
            "message": row["message"],
            "timestamp": row["timestamp"],
            "resolved": bool(row["resolved"]) if "resolved" in keys else False,
        }
