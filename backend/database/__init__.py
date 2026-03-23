"""Database abstraction layer."""

from backend.database.adapter import DatabaseAdapter
from backend.database.factory import get_adapter

__all__ = ["DatabaseAdapter", "get_adapter"]
