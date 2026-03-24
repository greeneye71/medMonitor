"""Demo data generator — physical simulation model with 6 scenarios."""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any

from backend.dependencies import get_db

logger = logging.getLogger(__name__)

# Speed multipliers: fraction of real time per simulated step (1 step = 10 sim minutes).
# interval = 10 * 60 * speed_factor  →  seconds between readings
#   1x:   600s  (10 min real  = 10 min sim  — real-time)
#   10x:   60s  ( 1 min real  = 10 min sim  — 10× faster)
#   60x:   10s  (10 sec real  = 10 min sim  — 60× faster)
#   600x:   1s  ( 1 sec real  = 10 min sim  — 600× faster)
SPEED_MAP = {
    "1x":   1.0,        # real-time
    "10x":  1 / 10,     # 10× faster
    "60x":  1 / 60,     # 60× faster
    "600x": 1 / 600,    # 600× faster
}

# Base temperatures for zones
BASE_TEMPS = {
    "fridge": 4.0,
    "freezer": -20.0,
}

# Scenario definitions
SCENARIOS = {
    "normal": {
        "description": "Temperature stabili, nessun allarme",
        "steps": 144,  # 24h at 10min intervals
        "events": {},
    },
    "fridge_alarm": {
        "description": "Frigorifero sale sopra soglia (porta aperta)",
        "steps": 144,
        "events": {
            "fridge": [(30, 90, 0.5)],  # (start_step, end_step, drift_per_step)
        },
    },
    "freezer_alarm": {
        "description": "Freezer scende sotto soglia (guasto termostato)",
        "steps": 144,
        "events": {
            "freezer": [(20, 80, -0.3)],
        },
    },
    "power_loss": {
        "description": "Entrambe le zone salgono per 2 ore (interruzione corrente)",
        "steps": 144,
        "events": {
            "fridge": [(40, 52, 1.5)],
            "freezer": [(40, 52, 1.0)],
        },
    },
    "sensor_battery_low": {
        "description": "Batteria scende a 0, sensore va offline",
        "steps": 144,
        "events": {},
        "battery_drain": True,
    },
    "full_stress": {
        "description": "Tutti gli scenari in sequenza",
        "steps": 288,  # 48h
        "events": {
            "fridge": [(30, 60, 0.5), (150, 180, 1.5)],
            "freezer": [(80, 120, -0.3), (200, 220, 1.0)],
        },
        "battery_drain": True,
    },
}


class DemoGenerator:
    """Generates simulated temperature data using a physical model.

    Model:
        next_temp = current
                  + (base - current) * 0.05   # mean reversion
                  + gauss(0, 0.15)             # gaussian noise
                  + scenario_drift             # scenario event
    """

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._scenario: str = "normal"
        self._speed: str = "10x"
        self._step: int = 0
        self._current_temps: dict[str, float] = {}
        self._battery: dict[str, int] = {}

    @property
    def is_active(self) -> bool:
        return self._running

    @property
    def status(self) -> dict[str, Any]:
        return {
            "active": self._running,
            "scenario": self._scenario,
            "speed": self._speed,
            "step": self._step,
            "temps": dict(self._current_temps),
        }

    async def start(self, scenario: str = "full_stress", speed: str = "10x") -> None:
        """Start demo generation."""
        if self._running:
            await self.stop()

        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")

        self._scenario = scenario
        self._speed = speed
        self._step = 0
        self._running = True

        # Initialize temperatures at base values
        self._current_temps = {
            "fridge": BASE_TEMPS["fridge"] + random.gauss(0, 0.5),
            "freezer": BASE_TEMPS["freezer"] + random.gauss(0, 0.5),
        }
        self._battery = {"fridge": 100, "freezer": 100}

        logger.info("Demo started: scenario=%s, speed=%s", scenario, speed)
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop demo generation."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Demo stopped at step %d", self._step)

    async def _run_loop(self) -> None:
        """Main generation loop."""
        scenario_def = SCENARIOS[self._scenario]
        total_steps = scenario_def["steps"]
        speed_factor = SPEED_MAP.get(self._speed, 1 / 60)

        # Interval between steps in real seconds
        interval = 10 * 60 * speed_factor  # 10 simulated minutes * speed

        # Minimum interval to avoid overloading
        interval = max(interval, 0.1)

        try:
            while self._running and self._step < total_steps:
                await self._generate_step(scenario_def)
                self._step += 1
                await asyncio.sleep(interval)

            if self._running:
                logger.info("Demo scenario '%s' completed (%d steps)", self._scenario, self._step)
                self._running = False

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Demo loop error: %s", e)
            self._running = False

    async def _generate_step(self, scenario_def: dict) -> None:
        """Generate one step of simulated data."""
        db = get_db()
        events = scenario_def.get("events", {})
        has_battery_drain = scenario_def.get("battery_drain", False)

        for zone in ["fridge", "freezer"]:
            base = BASE_TEMPS[zone]
            current = self._current_temps[zone]

            # Physical model
            mean_reversion = (base - current) * 0.05
            noise = random.gauss(0, 0.15)

            # Scenario drift
            drift = 0.0
            zone_events = events.get(zone, [])
            for start, end, event_drift in zone_events:
                if start <= self._step <= end:
                    drift = event_drift
                    break

            next_temp = current + mean_reversion + noise + drift
            self._current_temps[zone] = next_temp

            # Battery simulation
            battery = self._battery[zone]
            if has_battery_drain and self._step > 100:
                battery = max(0, battery - random.randint(0, 3))
                self._battery[zone] = battery

            # Skip writing if battery dead (sensor offline)
            if battery <= 0:
                continue

            sensor_id = f"0xDEMO_{zone.upper()}"
            reading = {
                "zone": zone,
                "sensor_id": sensor_id,
                "temperature": round(next_temp, 2),
                "humidity": round(random.uniform(30, 80), 1),
                "battery": battery,
                "timestamp": datetime.now(timezone.utc),
            }

            await db.write_reading(reading)


# Singleton
demo_generator = DemoGenerator()
