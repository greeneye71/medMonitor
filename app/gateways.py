"""Gateway registry: DATA_DIR/gateways.json, written by install.sh (the app only renames)."""
import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

FILE = "gateways.json"

log = logging.getLogger(__name__)


@dataclass
class Gateway:
    id: int
    name: str
    base_topic: str
    config: str
    frontend_port: int = 8080

    @property
    def container(self) -> str:
        """Quadlet container/unit name written by install.sh."""
        return "zigbee2mqtt" if self.id == 1 else f"zigbee2mqtt-{self.id}"


def _parse(raw) -> list[Gateway]:
    items = raw["gateways"]
    if not isinstance(items, list) or not items:
        raise ValueError("no gateways")
    gws = []
    for it in items:
        gid = it["id"]
        if not isinstance(gid, int) or isinstance(gid, bool):
            raise ValueError("bad id")
        gws.append(Gateway(gid, str(it["name"]), str(it["base_topic"]), str(it["config"]),
                           int(it.get("frontend_port", 8080))))
    if len({g.id for g in gws}) != len(gws):
        raise ValueError("duplicate id")
    if len({g.base_topic for g in gws}) != len(gws):
        raise ValueError("duplicate base_topic")
    return sorted(gws, key=lambda g: g.id)


def load(data_dir, fallback_config) -> list[Gateway]:
    path = Path(data_dir) / FILE
    fallback = [Gateway(1, "Gateway 1", "zigbee2mqtt", str(fallback_config), 8080)]
    if not path.exists():               # single gateway installed before v2.1
        return fallback
    try:
        return _parse(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("%s non valido (%s): uso il solo gateway 1", path, exc)
        return fallback


def by_id(gateways, gid) -> Gateway | None:
    return next((g for g in gateways if g.id == gid), None)


def rename(data_dir, gid, name) -> None:
    path = Path(data_dir) / FILE
    raw = json.loads(path.read_text(encoding="utf-8"))
    entry = next((it for it in raw["gateways"] if it.get("id") == gid), None)
    if entry is None:
        raise KeyError(gid)
    entry["name"] = name
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
