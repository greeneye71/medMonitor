"""Pydantic models for configuration and thresholds."""

from pydantic import BaseModel, Field


class ZoneThresholds(BaseModel):
    """Temperature thresholds for a zone."""
    min: float
    max: float


class SensorThreshold(BaseModel):
    """Per-sensor threshold configuration."""
    name: str = ""
    zone: str = "fridge"
    min: float | None = None
    max: float | None = None
    override: bool = False


class ThresholdsConfig(BaseModel):
    """Thresholds configuration with zone defaults and per-sensor overrides."""
    defaults: dict[str, ZoneThresholds] = Field(default_factory=lambda: {
        "fridge": ZoneThresholds(min=0.0, max=30.0),
        "freezer": ZoneThresholds(min=-30.0, max=0.0),
    })
    sensors: dict[str, SensorThreshold] = Field(default_factory=dict)

    def resolve(self, sensor_id: str) -> tuple[float, float]:
        """Return effective (min, max) for a sensor.

        If the sensor has override=True and individual thresholds,
        use those. Otherwise fall back to zone defaults.
        """
        sensor = self.sensors.get(sensor_id)
        if sensor and sensor.override and sensor.min is not None and sensor.max is not None:
            return (sensor.min, sensor.max)

        # Fall back to zone defaults
        zone = sensor.zone if sensor else "fridge"
        zone_defaults = self.defaults.get(zone, ZoneThresholds(min=0.0, max=30.0))
        return (zone_defaults.min, zone_defaults.max)


class SmtpConfig(BaseModel):
    """SMTP email configuration."""
    host: str = "smtp.example.com"
    port: int = 587
    use_tls: bool = True
    user: str = ""
    password: str = ""
    recipients: str = ""


class ImapConfig(BaseModel):
    """IMAP email configuration."""
    host: str = ""
    port: int = 993
    use_ssl: bool = True
    user: str = ""
    password: str = ""
    folder: str = "INBOX"
    check_interval_seconds: int = 120


class EmailConfig(BaseModel):
    """Combined email configuration."""
    smtp: SmtpConfig = Field(default_factory=SmtpConfig)
    imap: ImapConfig = Field(default_factory=ImapConfig)


class AppConfig(BaseModel):
    """Runtime application configuration (stored in config.json)."""
    app_name: str = "medMonitor"
    app_theme: str = "slate"
    log_level: str = "INFO"
    polling_interval_minutes: int = 10
    alert_cooldown_minutes: int = 30
    data_retention_days: int = 365
    database_backend: str = "tinyflux"
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)


class ConfigPatch(BaseModel):
    """Partial config update from API."""
    app_name: str | None = None
    app_theme: str | None = None
    log_level: str | None = None
    polling_interval_minutes: int | None = None
    alert_cooldown_minutes: int | None = None
    data_retention_days: int | None = None


class ThresholdDefaultsPatch(BaseModel):
    """Update zone default thresholds."""
    fridge: ZoneThresholds | None = None
    freezer: ZoneThresholds | None = None


class SensorThresholdPatch(BaseModel):
    """Update individual sensor thresholds."""
    min: float | None = None
    max: float | None = None
    override: bool | None = None
