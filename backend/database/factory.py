"""Database adapter factory — selects backend based on configuration."""

import logging

from backend.database.adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


def get_adapter(settings) -> DatabaseAdapter:
    """Create the appropriate database adapter based on DATABASE_BACKEND.

    Args:
        settings: Application settings with database_backend, tinyflux_path,
                  and postgres_dsn attributes.

    Returns:
        A DatabaseAdapter instance (TinyFluxAdapter or TimescaleAdapter).
    """
    backend = settings.database_backend.lower()

    if backend == "tinyflux":
        from backend.database.tinyflux_adapter import TinyFluxAdapter
        adapter = TinyFluxAdapter(settings.tinyflux_path)
        logger.info("Using TinyFlux adapter: %s", settings.tinyflux_path)
        return adapter

    if backend == "timescale":
        from backend.database.timescale_adapter import TimescaleAdapter
        adapter = TimescaleAdapter(settings.postgres_dsn)
        logger.info("Using TimescaleDB adapter: %s", settings.postgres_host)
        return adapter

    raise ValueError(
        f"Unknown DATABASE_BACKEND: '{backend}'. "
        "Supported values: 'tinyflux', 'timescale'"
    )
