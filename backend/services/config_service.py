"""Config service — hierarchical configuration with hot reload."""

import json
import logging
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.paths import data_file
from backend.models.config_model import (
    AppConfig,
    ThresholdsConfig,
    ZoneThresholds,
    SensorThreshold,
    SmtpConfig,
    ImapConfig,
    EmailConfig,
)

logger = logging.getLogger(__name__)

CONFIG_JSON_PATH = data_file("config.json")


class ConfigService:
    """Manages application configuration with 2-level hierarchy:

    1. .env / hardcoded defaults  (base — always re-read at startup)
    2. data/config.json           (UI delta — ONLY explicitly changed fields)

    config.json stores ONLY the delta: fields changed via the UI.
    This guarantees that .env changes are always picked up for unmodified fields,
    because the base is rebuilt from settings on every get_config() call.
    """

    def __init__(self) -> None:
        self._delta: dict[str, Any] = {}

    def get_config(self) -> AppConfig:
        """Load and return current configuration (hot reload each call)."""
        return self._load()

    def update_config(self, patch: dict[str, Any]) -> AppConfig:
        """Apply partial update and persist ONLY the changed fields to config.json."""
        # Merge patch into existing delta (load delta first to preserve previous UI changes)
        self._load_delta()
        self._delta.update({k: v for k, v in patch.items() if v is not None})
        self._save_delta()
        logger.info("Configuration updated: %s", list(patch.keys()))
        return self.get_config()

    def get_thresholds(self) -> ThresholdsConfig:
        """Return current thresholds configuration."""
        return self.get_config().thresholds

    def update_sensor_threshold(self, sensor_id: str, patch: dict[str, Any]) -> ThresholdsConfig:
        """Update individual sensor thresholds."""
        config = self.get_config()
        sensor = config.thresholds.sensors.get(sensor_id, SensorThreshold())

        for key, value in patch.items():
            if value is not None and hasattr(sensor, key):
                setattr(sensor, key, value)

        config.thresholds.sensors[sensor_id] = sensor
        self._load_delta()
        self._delta["thresholds"] = config.thresholds.model_dump()
        self._save_delta()
        logger.info("Sensor threshold updated: %s", sensor_id)
        return config.thresholds

    def update_zone_color(self, zone_name: str, color: str) -> None:
        """Persist a zone color in config.json."""
        self._load_delta()
        zone_colors = self._delta.get("zone_colors", {})
        zone_colors[zone_name] = color
        self._delta["zone_colors"] = zone_colors
        self._save_delta()

    def delete_zone_color(self, zone_name: str) -> None:
        """Remove a zone color from config.json."""
        self._load_delta()
        zone_colors = self._delta.get("zone_colors", {})
        zone_colors.pop(zone_name, None)
        self._delta["zone_colors"] = zone_colors
        self._save_delta()

    def delete_threshold_default(self, zone_name: str) -> None:
        """Remove a zone from thresholds.defaults in config.json."""
        self._load_delta()
        # Get current effective config to see all active zones
        current_cfg = self.get_config()
        # Build complete defaults snapshot without the deleted zone
        current_defaults = {}
        if current_cfg.thresholds.defaults:
            for zname, zthresh in current_cfg.thresholds.defaults.items():
                if zname != zone_name:
                    current_defaults[zname] = (
                        zthresh.model_dump() if hasattr(zthresh, "model_dump")
                        else {"min": zthresh.min, "max": zthresh.max}
                    )
        thresholds = self._delta.get("thresholds", {})
        thresholds["defaults"] = current_defaults
        self._delta["thresholds"] = thresholds
        self._save_delta()

    def delete_sensor_threshold(self, sensor_id: str) -> ThresholdsConfig:
        """Remove sensor-specific thresholds (revert to zone defaults)."""
        config = self.get_config()
        if sensor_id in config.thresholds.sensors:
            del config.thresholds.sensors[sensor_id]
            self._load_delta()
            self._delta["thresholds"] = config.thresholds.model_dump()
            self._save_delta()
            logger.info("Sensor threshold removed: %s", sensor_id)
        return config.thresholds

    def update_threshold_defaults(self, updates: dict[str, ZoneThresholds]) -> ThresholdsConfig:
        """Upsert zone defaults in thresholds.defaults.

        Args:
            updates: dict[str, ZoneThresholds] — zone name -> thresholds
        """
        config = self.get_config()
        for zone, thresholds in updates.items():
            config.thresholds.defaults[zone] = thresholds

        self._load_delta()
        self._delta["thresholds"] = config.thresholds.model_dump()
        self._save_delta()
        logger.info("Zone defaults updated: %s", list(updates.keys()))
        return config.thresholds

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> AppConfig:
        """Build config from .env base, then apply UI delta from config.json."""
        base = AppConfig(
            app_name=settings.app_name,
            app_theme=settings.app_theme,
            log_level=settings.log_level,
            polling_interval_minutes=settings.polling_interval_minutes,
            alert_cooldown_minutes=settings.alert_cooldown_minutes,
            data_retention_days=settings.data_retention_days,
            database_backend=settings.database_backend,
            thresholds=ThresholdsConfig(
                defaults={
                    "fridge": ZoneThresholds(
                        min=settings.fridge_temp_min,
                        max=settings.fridge_temp_max,
                    ),
                    "freezer": ZoneThresholds(
                        min=settings.freezer_temp_min,
                        max=settings.freezer_temp_max,
                    ),
                }
            ),
            email=EmailConfig(
                smtp=SmtpConfig(
                    host=settings.smtp_host,
                    port=settings.smtp_port,
                    use_tls=settings.smtp_use_tls,
                    user=settings.smtp_user,
                    password=settings.smtp_password,
                    recipients=settings.alert_recipients,
                ),
                imap=ImapConfig(
                    host=settings.imap_host,
                    port=settings.imap_port,
                    use_ssl=settings.imap_use_ssl,
                    user=settings.imap_user,
                    password=settings.imap_password,
                    folder=settings.imap_folder,
                    check_interval_seconds=settings.imap_check_interval_seconds,
                ),
            ),
        )

        delta = self._load_delta()
        if not delta:
            return base

        try:
            merged = {**base.model_dump(), **delta}
            return AppConfig(**merged)
        except Exception as e:
            logger.warning("Invalid config.json delta, using .env defaults: %s", e)
            return base

    def _load_delta(self) -> dict[str, Any]:
        """Read UI delta from config.json. Caches in self._delta."""
        if not CONFIG_JSON_PATH.exists():
            return {}
        try:
            text = CONFIG_JSON_PATH.read_text(encoding="utf-8").strip()
            if text:
                self._delta = json.loads(text)
                return self._delta
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Invalid config.json delta, ignoring: %s", e)
        return {}

    def _save_delta(self) -> None:
        """Persist only the UI delta to config.json (never the full config)."""
        CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_JSON_PATH.write_text(
            json.dumps(self._delta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Config delta saved: %s", list(self._delta.keys()))


# Singleton instance
config_service = ConfigService()
