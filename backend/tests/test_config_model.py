"""Test per config_model v2 — zone_colors, ThresholdDefaultsPatch generico."""

from backend.models.config_model import (
    AppConfig,
    ThresholdDefaultsPatch,
    ZoneThresholds,
)


def test_appconfig_zone_colors_default():
    cfg = AppConfig()
    assert "fridge" in cfg.zone_colors
    assert cfg.zone_colors["fridge"] == "#22c55e"
    assert "freezer" in cfg.zone_colors
    assert cfg.zone_colors["freezer"] == "#3b82f6"


def test_appconfig_archive_after_days_default():
    cfg = AppConfig()
    assert cfg.archive_after_days == 180


def test_threshold_defaults_patch_zones():
    patch = ThresholdDefaultsPatch(
        zones={"cold_room": ZoneThresholds(min=2.0, max=8.0)}
    )
    assert patch.zones is not None
    assert "cold_room" in patch.zones
    assert patch.zones["cold_room"].min == 2.0
