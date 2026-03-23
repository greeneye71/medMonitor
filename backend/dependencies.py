"""Shared dependencies — database adapter singleton."""

from backend.database.adapter import DatabaseAdapter
from backend.database.factory import get_adapter
from backend.config import settings

_db: DatabaseAdapter | None = None


def get_db() -> DatabaseAdapter:
    """Return the database adapter singleton, creating it if needed."""
    global _db
    if _db is None:
        _db = get_adapter(settings)
    return _db


async def close_db() -> None:
    """Close the database adapter."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
