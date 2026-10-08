"""Read/write gateway parameters in zigbee2mqtt configuration.yaml (other keys untouched)."""
import re
import socket
from pathlib import Path

import yaml

DEFAULT = {"ip": "", "port": 6638, "adapter": "ember", "channel": 11}


def read_gateway(path: str | Path) -> dict:
    path = Path(path)
    gw = dict(DEFAULT)
    if not path.exists():
        return gw
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return gw  # malformed file: show defaults, saving rewrites it
    if not isinstance(cfg, dict):
        return gw
    serial = cfg.get("serial") if isinstance(cfg.get("serial"), dict) else {}
    m = re.match(r"tcp://([^:/]+):(\d+)", str(serial.get("port", "")))
    if m:
        gw["ip"], gw["port"] = m.group(1), int(m.group(2))
    gw["adapter"] = serial.get("adapter") or gw["adapter"]
    advanced = cfg.get("advanced") if isinstance(cfg.get("advanced"), dict) else {}
    try:
        gw["channel"] = int(advanced.get("channel") or gw["channel"])
    except (TypeError, ValueError):
        pass
    return gw


def write_gateway(path: str | Path, ip: str, port: int, adapter: str, channel: int) -> None:
    path = Path(path)
    cfg = {}
    if path.exists():
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    if not isinstance(cfg.get("serial"), dict):
        cfg["serial"] = {}
    cfg["serial"]["port"] = f"tcp://{ip}:{int(port)}"
    cfg["serial"]["adapter"] = adapter
    if not isinstance(cfg.get("advanced"), dict):
        cfg["advanced"] = {}
    cfg["advanced"]["channel"] = int(channel)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    tmp.replace(path)


def test_connection(ip: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False
