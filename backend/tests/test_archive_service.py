"""Tests for ArchiveService."""
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_archive_creates_csv(tmp_path, monkeypatch):
    """Archive service deve creare CSV e aggiornare archive_log.json."""
    from backend.services.archive_service import ArchiveService

    mock_db = AsyncMock()
    mock_db.get_readings.return_value = [
        {"timestamp": (datetime.now(tz=timezone.utc) - timedelta(days=200)).isoformat(),
         "zone": "fridge", "sensor_id": "SEN-001", "temperature": 4.2,
         "humidity": None, "battery": 87},
    ]
    mock_db.get_alerts.return_value = []
    mock_db.delete_readings_before = AsyncMock(return_value=1)
    mock_db.delete_alerts_before = AsyncMock(return_value=0)

    mock_cfg_svc = MagicMock()
    mock_cfg_svc.get_config.return_value = MagicMock(archive_after_days=180)

    monkeypatch.setattr("backend.services.archive_service.ARCHIVE_DIR", tmp_path / "archive")

    svc = ArchiveService(db=mock_db, config_service=mock_cfg_svc)
    result = await svc.run()

    assert result["rows_archived"] >= 1
    log_file = tmp_path / "archive" / "archive_log.json"
    assert log_file.exists()
    log = json.loads(log_file.read_text())
    assert log["last_rows_archived"] >= 1
