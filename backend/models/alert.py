"""Pydantic models for alerts."""

from datetime import datetime
from pydantic import BaseModel


class Alert(BaseModel):
    """An alert record."""
    zone: str
    sensor_id: str
    temperature: float
    level: str  # "WARNING" | "CRITICAL"
    threshold_min: float
    threshold_max: float
    message: str = ""
    timestamp: datetime


class AlertTestRequest(BaseModel):
    """Request to send a test alert email."""
    email: str
