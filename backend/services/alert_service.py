"""Alert service — checks thresholds every 60s, sends email alerts."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from backend.dependencies import get_db
from backend.services.config_service import config_service
from backend.services.email_service import send_alert_email

logger = logging.getLogger(__name__)


class AlertService:
    """APScheduler-compatible alert checker.

    Levels:
    - WARNING: out of range 0-15 minutes
    - CRITICAL: out of range > 15 minutes

    Cooldown: configurable (default 30 min) between repeat emails per sensor.
    """

    def __init__(self) -> None:
        # sensor_id -> datetime of first out-of-range reading
        self._out_of_range_since: dict[str, datetime] = {}
        # sensor_id -> datetime of last email sent
        self._last_email_sent: dict[str, datetime] = {}

    async def restore_state(self) -> None:
        """Restore in-memory tracking state from the DB after a restart.

        Loads the most recent alert per sensor within the cooldown window so
        that we don't fire duplicate emails immediately after a restart, and so
        that a sensor already CRITICAL before the restart continues to be treated
        as CRITICAL rather than being reset to WARNING.
        """
        try:
            db = get_db()
            config = config_service.get_config()
            cooldown = config.alert_cooldown_minutes
            # Look back 2× the cooldown so we catch the most recent alert
            from_dt = datetime.now(timezone.utc) - timedelta(minutes=cooldown * 2)
            recent_alerts = await db.get_alerts(from_dt=from_dt)

            for alert in recent_alerts:
                sensor_id = alert.get("sensor_id", "")
                ts: Optional[datetime] = alert.get("timestamp")
                if not ts or not sensor_id:
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                # Keep only the most recent per sensor
                prev = self._last_email_sent.get(sensor_id)
                if prev is None or ts > prev:
                    self._last_email_sent[sensor_id] = ts

            if self._last_email_sent:
                logger.info(
                    "AlertService restored cooldown state for %d sensor(s)",
                    len(self._last_email_sent),
                )
        except Exception as e:
            logger.warning("Failed to restore alert state (non-fatal): %s", e)

    async def check_alerts(self) -> None:
        """Main check loop — called every 60 seconds."""
        try:
            db = get_db()
            config = config_service.get_config()
            thresholds = config.thresholds
            cooldown_minutes = config.alert_cooldown_minutes

            latest_readings = await db.get_latest()

            for reading in latest_readings:
                sensor_id = reading["sensor_id"]

                # Skip demo sensors in normal check
                if sensor_id.startswith("0xDEMO"):
                    continue

                temperature = reading["temperature"]
                eff_min, eff_max = thresholds.resolve(sensor_id)

                if temperature < eff_min or temperature > eff_max:
                    await self._handle_out_of_range(
                        db, reading, eff_min, eff_max, cooldown_minutes,
                    )
                else:
                    # Back in range — clear tracking
                    self._out_of_range_since.pop(sensor_id, None)

        except Exception as e:
            logger.error("alert_service.check_alerts failed: %s", e, exc_info=True)
            # Do not re-raise — APScheduler logs but doesn't crash

    async def _handle_out_of_range(
        self,
        db,
        reading: dict[str, Any],
        eff_min: float,
        eff_max: float,
        cooldown_minutes: int,
    ) -> None:
        sensor_id = reading["sensor_id"]
        now = datetime.now(timezone.utc)

        # Track when sensor first went out of range
        if sensor_id not in self._out_of_range_since:
            self._out_of_range_since[sensor_id] = now

        out_since = self._out_of_range_since[sensor_id]
        duration = (now - out_since).total_seconds() / 60  # minutes

        # Determine level
        if duration > 15:
            level = "CRITICAL"
        else:
            level = "WARNING"

        # Check cooldown
        last_sent = self._last_email_sent.get(sensor_id)
        if last_sent:
            elapsed = (now - last_sent).total_seconds() / 60
            if elapsed < cooldown_minutes:
                return

        # Build alert
        alert = {
            "zone": reading["zone"],
            "sensor_id": sensor_id,
            "temperature": reading["temperature"],
            "level": level,
            "threshold_min": eff_min,
            "threshold_max": eff_max,
            "message": self._build_message(reading, level, eff_min, eff_max, duration),
            "timestamp": now,
        }

        # Write to DB
        await db.write_alert(alert)
        logger.warning(
            "ALERT [%s] sensor %s: %.1f°C (range %.1f-%.1f, %d min)",
            level, sensor_id, reading["temperature"], eff_min, eff_max, int(duration),
        )

        # Send email
        try:
            await send_alert_email(alert)
            self._last_email_sent[sensor_id] = now
        except Exception as e:
            logger.error("Failed to send alert email for %s: %s", sensor_id, e)

    @staticmethod
    def _build_message(
        reading: dict, level: str, eff_min: float, eff_max: float, duration: float,
    ) -> str:
        temp = reading["temperature"]
        zone = reading["zone"]
        sensor = reading["sensor_id"]

        if level == "CRITICAL":
            prefix = "ALLARME CRITICO"
        else:
            prefix = "AVVISO"

        return (
            f"{prefix}: Sensore {sensor} ({zone}) a {temp:.1f}°C "
            f"fuori soglia ({eff_min:.1f}–{eff_max:.1f}°C) "
            f"da {int(duration)} minuti."
        )


# Singleton
alert_service = AlertService()
