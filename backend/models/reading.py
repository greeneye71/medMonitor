"""Pydantic models for temperature readings and sensors."""

from datetime import datetime
from pydantic import BaseModel


class Reading(BaseModel):
    """A temperature reading from a sensor."""
    zone: str
    sensor_id: str
    temperature: float
    humidity: float | None = None
    battery: int | None = None
    timestamp: datetime


class Sensor(BaseModel):
    """A registered sensor."""
    sensor_id: str
    name: str = ""
    zone: str = "fridge"
    active: bool = True
    last_seen: datetime | None = None
    last_temperature: float | None = None
    battery: int | None = None


class SensorUpdate(BaseModel):
    """Update sensor name/zone."""
    name: str | None = None
    zone: str | None = None
    active: bool | None = None
