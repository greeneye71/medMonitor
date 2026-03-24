"""Application settings with hierarchical configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_backend: str = "tinyflux"
    tinyflux_path: str = "./data/temperature.db"
    postgres_user: str = "medmon"
    postgres_password: str = "cambia_questa_password"
    postgres_db: str = "medmonitor"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    # ZigBee
    zigbee_gateway_ip: str = "192.168.1.100"

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    alert_recipients: str = ""

    # IMAP
    imap_host: str = ""
    imap_port: int = 993
    imap_use_ssl: bool = True
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_check_interval_seconds: int = 120

    # Application
    app_name: str = "medMonitor"
    app_theme: str = "slate"
    log_level: str = "INFO"
    polling_interval_minutes: int = 10
    alert_cooldown_minutes: int = 30
    data_retention_days: int = 365

    # Thresholds (zone defaults)
    fridge_temp_min: float = 0.0
    fridge_temp_max: float = 30.0
    freezer_temp_min: float = -30.0
    freezer_temp_max: float = 0.0

    # Demo
    demo_mode: bool = False
    demo_speed: str = "10x"

    # CORS
    cors_origins: str = "http://localhost:8050"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
