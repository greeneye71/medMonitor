"""Config service — hierarchical configuration with hot reload."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from backend.config import settings
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

CONFIG_JSON_PATH = Path("data/config.json")


class ConfigService:
    """Manages application configuration with 3-level hierarchy:
    1. data/config.json (highest priority — UI modifications)
    2. .env file (initial configuration)
    3. hardcoded defaults (config.py)
    """

    def __init__(self) -> None:
        self._config: AppConfig | None = None

    def get_config(self) -> AppConfig:
        """Load and return current configuration (hot reload)."""
        self._config = self._load()
        return self._config

    def update_config(self, patch: dict[str, Any]) -> AppConfig:
        """Apply partial update and persist to config.json."""
        config = self.get_config()
        data = config.model_dump()

        for key, value in patch.items():
            if value is not None and key in data:
                data[key] = value

        self._config = AppConfig(**data)
        self._save(self._config)
        logger.info("Configuration updated: %s", list(patch.keys()))
        return self._config

    def get_thresholds(self) -> ThresholdsConfig:
        """Return current thresholds configuration."""
        return self.get_config().thresholds

    def update_threshold_defaults(self, updates: dict[str, ZoneThresholds]) -> ThresholdsConfig:
        """Update zone default thresholds."""
        config = self.get_config()
        for zone, thresholds in updates.items():
            config.thresholds.defaults[zone] = thresholds

        self._save(config)
        logger.info("Zone defaults updated: %s", list(updates.keys()))
        return config.thresholds

    def update_sensor_threshold(self, sensor_id: str, patch: dict[str, Any]) -> ThresholdsConfig:
        """Update individual sensor thresholds."""
        config = self.get_config()
        sensor = config.thresholds.sensors.get(sensor_id, SensorThreshold())

        for key, value in patch.items():
            if value is not None and hasattr(sensor, key):
                setattr(sensor, key, value)

        config.thresholds.sensors[sensor_id] = sensor
        self._save(config)
        logger.info("Sensor threshold updated: %s", sensor_id)
        return config.thresholds

    def delete_sensor_threshold(self, sensor_id: str) -> ThresholdsConfig:
        """Remove sensor-specific thresholds (revert to zone defaults)."""
        config = self.get_config()
        if sensor_id in config.thresholds.sensors:
            del config.thresholds.sensors[sensor_id]
            self._save(config)
            logger.info("Sensor threshold removed: %s", sensor_id)
        return config.thresholds

    def _load(self) -> AppConfig:
        """Load config with hierarchy: defaults → .env → config.json."""
        # Start with defaults from .env / hardcoded
        config = AppConfig(
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

        # Override with config.json (highest priority)
        if CONFIG_JSON_PATH.exists():
            try:
                with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                    json_data = f.read().strip()
                    if json_data:
                        data = json.loads(json_data)
                        config = AppConfig(**{**config.model_dump(), **data})
                        logger.debug("Loaded config.json overrides")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Invalid config.json, using defaults: %s", e)

        return config

    def _save(self, config: AppConfig) -> None:
        """Persist configuration to config.json."""
        os.makedirs(CONFIG_JSON_PATH.parent, exist_ok=True)
        with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)
        logger.debug("Config saved to %s", CONFIG_JSON_PATH)


# Singleton instance
config_service = ConfigService()
