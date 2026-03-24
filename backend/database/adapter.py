"""Abstract Database Adapter — interface for all database backends."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class DatabaseAdapter(ABC):
    """Abstract base class defining the database interface.

    Both TinyFluxAdapter and TimescaleAdapter implement this interface,
    allowing seamless switching between backends.
    """

    @abstractmethod
    async def write_reading(self, reading: dict[str, Any]) -> None:
        """Write a temperature reading.

        Args:
            reading: dict with keys:
                - zone: str ("fridge" | "freezer")
                - sensor_id: str
                - temperature: float
                - humidity: float | None
                - battery: int | None
                - timestamp: datetime
        """

    @abstractmethod
    async def get_readings(
        self,
        zone: str | None = None,
        sensor_id: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get temperature readings with optional filters.

        Returns list of dicts with same keys as write_reading.
        """

    @abstractmethod
    async def get_latest(self) -> list[dict[str, Any]]:
        """Get the latest reading for each sensor.

        Returns list of dicts, one per sensor, with most recent reading.
        """

    @abstractmethod
    async def write_alert(self, alert: dict[str, Any]) -> None:
        """Write an alert record.

        Args:
            alert: dict with keys:
                - zone: str
                - sensor_id: str
                - temperature: float
                - level: str ("WARNING" | "CRITICAL")
                - threshold_min: float
                - threshold_max: float
                - message: str
                - timestamp: datetime
        """

    @abstractmethod
    async def get_alerts(
        self,
        zone: str | None = None,
        level: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get alert records with optional filters."""

    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved.

        Returns True if the alert was found and updated, False otherwise.
        Note: TinyFlux does not support in-place updates; implementations
        should return False gracefully if the backend does not support it.
        """

    @abstractmethod
    async def delete_demo_data(self) -> int:
        """Delete all demo data (sensor_id starting with '0xDEMO').

        Returns the number of deleted records.
        """

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (close connections, files, etc.)."""
