"""Tests for ConfigService and ThresholdsConfig."""

import json
import pytest
from pathlib import Path

from backend.models.config_model import ThresholdsConfig, ZoneThresholds, SensorThreshold


def test_resolve_defaults():
    """Sensor without override uses zone defaults."""
    config = ThresholdsConfig(
        defaults={"fridge": ZoneThresholds(min=0, max=30)},
        sensors={"0xABC": SensorThreshold(zone="fridge", override=False)},
    )
    eff_min, eff_max = config.resolve("0xABC")
    assert eff_min == 0.0
    assert eff_max == 30.0


def test_resolve_with_override():
    """Sensor with override uses individual thresholds."""
    config = ThresholdsConfig(
        defaults={"fridge": ZoneThresholds(min=0, max=30)},
        sensors={"0xABC": SensorThreshold(zone="fridge", min=2.0, max=8.0, override=True)},
    )
    eff_min, eff_max = config.resolve("0xABC")
    assert eff_min == 2.0
    assert eff_max == 8.0


def test_resolve_unknown_sensor():
    """Unknown sensor falls back to fridge defaults."""
    config = ThresholdsConfig(
        defaults={"fridge": ZoneThresholds(min=0, max=30)},
    )
    eff_min, eff_max = config.resolve("0xUNKNOWN")
    assert eff_min == 0.0
    assert eff_max == 30.0


def test_resolve_override_without_values():
    """Override=True but no min/max falls back to zone defaults."""
    config = ThresholdsConfig(
        defaults={"freezer": ZoneThresholds(min=-30, max=0)},
        sensors={"0xABC": SensorThreshold(zone="freezer", min=None, max=None, override=True)},
    )
    eff_min, eff_max = config.resolve("0xABC")
    assert eff_min == -30.0
    assert eff_max == 0.0


def test_config_service_load(tmp_path, monkeypatch):
    """ConfigService loads from .env defaults when no config.json exists."""
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", tmp_path / "config.json")

    from backend.services.config_service import ConfigService
    service = ConfigService()
    config = service.get_config()

    assert config.app_name == "medMonitor"
    assert config.database_backend == "tinyflux"


def test_config_service_save_and_reload(tmp_path, monkeypatch):
    """ConfigService persists and reloads changes."""
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", config_path)

    from backend.services.config_service import ConfigService
    service = ConfigService()

    service.update_config({"app_name": "TestMonitor"})
    assert config_path.exists()

    # Reload
    service2 = ConfigService()
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", config_path)
    config = service2.get_config()
    assert config.app_name == "TestMonitor"


def test_config_service_threshold_update(tmp_path, monkeypatch):
    """ConfigService updates and persists sensor thresholds."""
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", tmp_path / "config.json")

    from backend.services.config_service import ConfigService
    service = ConfigService()

    thresholds = service.update_sensor_threshold("0xNEW", {"min": 1.0, "max": 7.0, "override": True})
    assert "0xNEW" in thresholds.sensors
    assert thresholds.sensors["0xNEW"].min == 1.0

    eff_min, eff_max = thresholds.resolve("0xNEW")
    assert eff_min == 1.0
    assert eff_max == 7.0


def test_config_service_delete_threshold(tmp_path, monkeypatch):
    """ConfigService deletes sensor thresholds."""
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", tmp_path / "config.json")

    from backend.services.config_service import ConfigService
    service = ConfigService()

    service.update_sensor_threshold("0xDEL", {"min": 1.0, "max": 5.0, "override": True})
    thresholds = service.delete_sensor_threshold("0xDEL")
    assert "0xDEL" not in thresholds.sensors


def test_update_zone_color(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", tmp_path / "config.json")
    from backend.services.config_service import ConfigService
    svc = ConfigService()
    svc.update_zone_color("cold_room", "#a855f7")
    cfg = svc.get_config()
    assert cfg.zone_colors.get("cold_room") == "#a855f7"


def test_delete_zone_color(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", tmp_path / "config.json")
    from backend.services.config_service import ConfigService
    svc = ConfigService()
    svc.update_zone_color("cold_room", "#a855f7")
    svc.delete_zone_color("cold_room")
    cfg = svc.get_config()
    assert "cold_room" not in cfg.zone_colors
