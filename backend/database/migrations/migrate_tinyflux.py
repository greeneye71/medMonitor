"""Migrate data from TinyFlux to TimescaleDB.

Usage:
    python -m backend.database.migrations.migrate_tinyflux \
        --tinyflux-path ./data/temperature.db \
        --postgres-dsn postgresql://medmon:password@localhost/medmonitor \
        --dry-run
"""

import argparse
import asyncio
import logging
import sys

import asyncpg
from tinyflux import TinyFlux, TagQuery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


async def migrate(tinyflux_path: str, postgres_dsn: str, dry_run: bool) -> None:
    logger.info("Opening TinyFlux: %s", tinyflux_path)
    db = TinyFlux(tinyflux_path)

    tag_q = TagQuery()

    # Gather readings
    readings = db.search(tag_q.measurement == "temperature")
    alerts = db.search(tag_q.measurement == "alert")

    logger.info("Found %d readings and %d alerts to migrate", len(readings), len(alerts))

    if dry_run:
        logger.info("[DRY RUN] No data written. Exiting.")
        db.close()
        return

    logger.info("Connecting to TimescaleDB: %s", postgres_dsn)
    conn = await asyncpg.connect(postgres_dsn)

    try:
        # Migrate readings in batches
        migrated_readings = 0
        for i in range(0, len(readings), BATCH_SIZE):
            batch = readings[i : i + BATCH_SIZE]
            records = []
            for r in batch:
                battery = r.fields.get("battery", -1)
                records.append((
                    r.tags.get("zone", ""),
                    r.tags.get("sensor_id", ""),
                    float(r.fields.get("temperature", 0.0)),
                    float(r.fields.get("humidity", 0.0)) or None,
                    int(battery) if battery >= 0 else None,
                    r.time,
                ))

            await conn.executemany(
                """
                INSERT INTO temperature_readings
                    (zone, sensor_id, temperature, humidity, battery, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING
                """,
                records,
            )
            migrated_readings += len(batch)
            logger.info("Readings: %d / %d", migrated_readings, len(readings))

        # Migrate alerts in batches
        migrated_alerts = 0
        for i in range(0, len(alerts), BATCH_SIZE):
            batch = alerts[i : i + BATCH_SIZE]
            records = []
            for a in batch:
                records.append((
                    a.tags.get("zone", ""),
                    a.tags.get("sensor_id", ""),
                    float(a.fields.get("temperature", 0.0)),
                    a.tags.get("level", "WARNING"),
                    float(a.fields.get("threshold_min", 0.0)),
                    float(a.fields.get("threshold_max", 0.0)),
                    str(a.fields.get("message", "")),
                    a.time,
                ))

            await conn.executemany(
                """
                INSERT INTO alerts
                    (zone, sensor_id, temperature, level, threshold_min,
                     threshold_max, message, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                records,
            )
            migrated_alerts += len(batch)
            logger.info("Alerts: %d / %d", migrated_alerts, len(alerts))

        logger.info(
            "Migration complete: %d readings, %d alerts",
            migrated_readings, migrated_alerts,
        )

    finally:
        await conn.close()
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate TinyFlux → TimescaleDB")
    parser.add_argument("--tinyflux-path", required=True, help="Path to TinyFlux DB file")
    parser.add_argument("--postgres-dsn", required=True, help="PostgreSQL DSN")
    parser.add_argument("--dry-run", action="store_true", help="Count records without writing")
    args = parser.parse_args()

    asyncio.run(migrate(args.tinyflux_path, args.postgres_dsn, args.dry_run))


if __name__ == "__main__":
    main()
