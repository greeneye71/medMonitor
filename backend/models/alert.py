"""Pydantic models for alerts."""

from datetime import datetime
from pydantic import BaseModel, Field


class Alert(BaseModel):
    """An alert record."""
    id: str = ""
    zone: str
    sensor_id: str
    temperature: float
    level: str  # "WARNING" | "CRITICAL"
    threshold_min: float
    threshold_max: float
    message: str = ""
    timestamp: datetime
    resolved: bool = False


class AlertTestRequest(BaseModel):
    """Request to send a test alert email."""
    email: str
