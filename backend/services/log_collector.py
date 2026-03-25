"""Circular log buffer — raccoglie ultime N righe per GET /api/logs."""

import logging
from collections import deque
from datetime import datetime, timezone


class LogCollectorHandler(logging.Handler):
    """logging.Handler che accumula entry in un deque thread-safe."""

    def __init__(self, maxlen: int = 1000) -> None:
        super().__init__()
        self._buffer: deque[dict] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._buffer.append({
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "level":   record.levelname,
                "service": record.name,
                "message": record.getMessage(),
            })
        except Exception:
            pass  # Non crasha mai il logger

    def get_entries(
        self,
        level: str = "ALL",
        limit: int = 200,
    ) -> list[dict]:
        """Return last `limit` entries filtered by level."""
        entries = list(self._buffer)
        if level != "ALL":
            entries = [e for e in entries if e["level"] == level]
        return entries[-limit:]
