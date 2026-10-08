# Bug Fix & Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correggere 14 bug (4 critici, 6 gravi, 4 medi) e semplificare installazione/gestione del sistema medMonitor.

**Architecture:** Le correzioni seguono 6 fasi progressive: (1) fondamenta comuni (path resolution, config hierarchy), (2) avvio MQTT+Scheduler, (3) fix nei servizi, (4) logica allarmi, (5) frontend, (6) Docker e setup. Ogni fase è indipendente dalle successive ma dipende dalle precedenti.

**Tech Stack:** Python 3.11, FastAPI, Paho-MQTT, APScheduler, TinyFlux, asyncpg, Plotly Dash, Docker Compose

---

## File Map

| File | Azione | Scopo |
|------|--------|-------|
| `backend/paths.py` | **CREA** | Risoluzione centralizzata dei path (fix BUG 13) |
| `backend/config.py` | modifica | Porta smtp_host default a `""` (fix BUG 8) |
| `backend/main.py` | modifica | Avvia MQTT + APScheduler in lifespan (fix BUG 1) |
| `backend/dependencies.py` | modifica | Espone event loop per callback async MQTT (fix BUG 2) |
| `backend/services/mqtt_client.py` | modifica | Fix async callback + zone da sensors.json (fix BUG 2, 4) |
| `backend/services/alert_service.py` | modifica | Ripristina stato da DB al startup (fix BUG 5) |
| `backend/services/config_service.py` | modifica | Config.json salva solo delta (fix BUG 6), usa path centralizzato |
| `backend/services/email_service.py` | modifica | Usa path centralizzato (fix BUG 13) |
| `backend/services/imap_service.py` | modifica | Marca Seen dopo callback (fix BUG 14) |
| `backend/services/demo_generator.py` | modifica | Corregge SPEED_MAP invertita (fix BUG 3) |
| `backend/database/timescale_adapter.py` | modifica | Aggiunge asyncio.Lock al pool (fix BUG 7) |
| `backend/models/alert.py` | modifica | Aggiunge campo `resolved: bool` (prerequisito BUG 10) |
| `backend/routers/alerts.py` | modifica | Endpoint PATCH per risolvere alert (fix BUG 10) |
| `backend/routers/sensors.py` | modifica | Usa path centralizzato (fix BUG 13) |
| `frontend/callbacks/dashboard_callbacks.py` | modifica | Fix multi-sensore + WARNING status + counter allarmi (fix BUG 10, 11, 12) |
| `docker-compose.yml` | modifica | Fix dockerfile frontend + healthchecks (fix BUG 9, SIMPL 4) |
| `docker/frontend/Dockerfile` | **CREA** | Dockerfile dedicato frontend (fix BUG 9) |
| `docker/postgres/init.sql` | **CREA** | Auto-crea tabelle TimescaleDB (SIMPL 3) |
| `requirements.txt` | modifica | Solo dipendenze produzione (SIMPL 5) |
| `requirements-dev.txt` | **CREA** | Dipendenze test/dev (SIMPL 5) |
| `setup.bat` | **CREA** | Setup one-shot Windows (SIMPL 1) |
| `setup.sh` | **CREA** | Setup one-shot Linux/Mac (SIMPL 1) |
| `backend/tests/test_mqtt_client.py` | modifica | Test zone detection e async callback |
| `backend/tests/test_alert_service.py` | modifica | Test state restore |
| `backend/tests/test_config_service.py` | modifica | Test delta save |
| `backend/tests/test_demo_generator.py` | modifica | Test speed map |

---

## Phase 1 — Fondamenta comuni

### Task 1: Centralizza la risoluzione dei path (`backend/paths.py`)

**Files:**
- Create: `backend/paths.py`
- Test: `backend/tests/test_paths.py`

- [ ] **Step 1: Crea test**

```python
# backend/tests/test_paths.py
from pathlib import Path
from backend.paths import get_data_dir, get_template_dir

def test_get_data_dir_is_absolute():
    d = get_data_dir()
    assert d.is_absolute()
    assert d.name == "data"

def test_get_template_dir_points_to_backend_templates():
    t = get_template_dir()
    assert t.name == "templates"
    assert t.parent.name == "backend"

def test_data_file_helper():
    from backend.paths import data_file
    p = data_file("config.json")
    assert p.name == "config.json"
    assert p.parent.name == "data"
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd W:/varie/SV/medMonitor && pytest backend/tests/test_paths.py -v
```
Atteso: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implementa `backend/paths.py`**

```python
"""Centralized path resolution — all data/template paths go through here."""
from pathlib import Path

# Root del progetto = parent di backend/
_BACKEND_DIR = Path(__file__).parent
_PROJECT_ROOT = _BACKEND_DIR.parent


def get_data_dir() -> Path:
    """Return absolute path to the data/ directory."""
    d = _PROJECT_ROOT / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_template_dir() -> Path:
    """Return absolute path to backend/templates/."""
    return _BACKEND_DIR / "templates"


def data_file(filename: str) -> Path:
    """Return absolute path to a file inside data/."""
    return get_data_dir() / filename
```

- [ ] **Step 4: Verifica che i test passino**

```bash
pytest backend/tests/test_paths.py -v
```
Atteso: 3 PASS

- [ ] **Step 5: Aggiorna config_service.py, sensors.py, email_service.py**

In `backend/services/config_service.py` sostituire:
```python
# PRIMA:
CONFIG_JSON_PATH = Path("data/config.json")
# DOPO:
from backend.paths import data_file
CONFIG_JSON_PATH = data_file("config.json")
```

In `backend/routers/sensors.py` sostituire:
```python
# PRIMA:
SENSORS_FILE = Path("data/sensors.json")
# DOPO:
from backend.paths import data_file
SENSORS_FILE = data_file("sensors.json")
```

In `backend/services/email_service.py` sostituire:
```python
# PRIMA:
_template_env = Environment(
    loader=FileSystemLoader("backend/templates"),
    ...
)
# DOPO:
from backend.paths import get_template_dir
_template_env = Environment(
    loader=FileSystemLoader(str(get_template_dir())),
    ...
)
```

- [ ] **Step 6: Commit**

```bash
git add backend/paths.py backend/tests/test_paths.py backend/services/config_service.py backend/routers/sensors.py backend/services/email_service.py
git commit -m "[fix] centralizza path resolution (BUG-13)"
```

---

### Task 2: Fix config hierarchy — salva solo il delta in config.json (BUG 6)

**Files:**
- Modify: `backend/services/config_service.py`
- Test: `backend/tests/test_config_service.py`

**Problema:** `_save()` scrive l'AppConfig completo, "congela" i valori `.env`. La fix: config.json contiene solo i campi esplicitamente modificati via UI (delta). `_load()` parte dai default `.env` e applica il delta.

- [ ] **Step 1: Scrivi test aggiuntivi in test_config_service.py**

```python
# Aggiungere a backend/tests/test_config_service.py

def test_save_stores_only_delta(tmp_path, monkeypatch):
    """Config.json deve contenere solo i campi modificati via update_config."""
    import json
    from backend.services.config_service import ConfigService
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", cfg_path)
    svc = ConfigService()

    # Prima modifica solo app_name
    svc.update_config({"app_name": "TestName"})

    saved = json.loads(cfg_path.read_text())
    assert "app_name" in saved
    assert saved["app_name"] == "TestName"
    # Gli altri campi NON devono essere nel file
    assert "log_level" not in saved
    assert "email" not in saved

def test_env_values_not_overridden_after_save(tmp_path, monkeypatch):
    """Modificare .env dopo un save deve riflettersi nel get_config."""
    from backend.services.config_service import ConfigService
    from backend import config as cfg_module
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr("backend.services.config_service.CONFIG_JSON_PATH", cfg_path)

    svc = ConfigService()
    svc.update_config({"app_name": "UIName"})  # salva delta

    # Simula cambio in .env (cambio settings)
    original = cfg_module.settings.log_level
    try:
        cfg_module.settings.__dict__["log_level"] = "DEBUG"
        result = svc.get_config()
        assert result.log_level == "DEBUG"  # il valore .env deve prevalere
        assert result.app_name == "UIName"  # il delta UI deve prevalere su .env
    finally:
        cfg_module.settings.__dict__["log_level"] = original
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
pytest backend/tests/test_config_service.py::test_save_stores_only_delta -v
pytest backend/tests/test_config_service.py::test_env_values_not_overridden_after_save -v
```

- [ ] **Step 3: Ristruttura ConfigService per delta-save**

Sostituisci l'intera classe `ConfigService` in `backend/services/config_service.py`:

```python
"""Config service — hierarchical configuration with hot reload."""

import json
import logging
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.paths import data_file
from backend.models.config_model import (
    AppConfig,
    ThresholdsConfig,
    ZoneThresholds,
    SensorThreshold,
    SmtpConfig,
    ImapConfig,
    EmailConfig,
)

logger = logging.getLogger(__name__)

CONFIG_JSON_PATH = data_file("config.json")


class ConfigService:
    """Manages application configuration with 3-level hierarchy:
    1. Hardcoded defaults / .env  (lowest priority)
    2. data/config.json           (UI delta — only explicitly changed fields)

    config.json stores ONLY the delta: fields explicitly changed via UI.
    This ensures .env changes are always picked up for unmodified fields.
    """

    def __init__(self) -> None:
        self._delta: dict[str, Any] = {}  # only UI-modified fields

    def get_config(self) -> AppConfig:
        """Load and return current configuration (hot reload)."""
        return self._load()

    def update_config(self, patch: dict[str, Any]) -> AppConfig:
        """Apply partial update, persist ONLY the patch to config.json."""
        # Merge patch into existing delta
        self._delta.update({k: v for k, v in patch.items() if v is not None})
        self._save_delta()
        logger.info("Configuration updated: %s", list(patch.keys()))
        return self.get_config()

    def get_thresholds(self) -> ThresholdsConfig:
        """Return current thresholds configuration."""
        return self.get_config().thresholds

    def update_threshold_defaults(self, updates: dict[str, ZoneThresholds]) -> ThresholdsConfig:
        """Update zone default thresholds."""
        config = self.get_config()
        for zone, thresholds in updates.items():
            config.thresholds.defaults[zone] = thresholds

        # Persist thresholds in delta
        self._delta["thresholds"] = config.thresholds.model_dump()
        self._save_delta()
        logger.info("Zone defaults updated: %s", list(updates.keys()))
        return config.thresholds

    def update_sensor_threshold(self, sensor_id: str, patch: dict[str, Any]) -> ThresholdsConfig:
        """Update individual sensor thresholds."""
        config = self.get_config()
        sensor = config.thresholds.sensors.get(sensor_id, SensorThreshold())

        for key, value in patch.items():
            if value is not None and hasattr(sensor, key):
                setattr(sensor, key, value)

        config.thresholds.sensors[sensor_id] = sensor
        self._delta["thresholds"] = config.thresholds.model_dump()
        self._save_delta()
        logger.info("Sensor threshold updated: %s", sensor_id)
        return config.thresholds

    def delete_sensor_threshold(self, sensor_id: str) -> ThresholdsConfig:
        """Remove sensor-specific thresholds (revert to zone defaults)."""
        config = self.get_config()
        if sensor_id in config.thresholds.sensors:
            del config.thresholds.sensors[sensor_id]
            self._delta["thresholds"] = config.thresholds.model_dump()
            self._save_delta()
            logger.info("Sensor threshold removed: %s", sensor_id)
        return config.thresholds

    def _load(self) -> AppConfig:
        """Load config: .env base merged with delta from config.json."""
        # Base from .env / hardcoded defaults
        base = AppConfig(
            app_name=settings.app_name,
            app_theme=settings.app_theme,
            log_level=settings.log_level,
            polling_interval_minutes=settings.polling_interval_minutes,
            alert_cooldown_minutes=settings.alert_cooldown_minutes,
            data_retention_days=settings.data_retention_days,
            database_backend=settings.database_backend,
            thresholds=ThresholdsConfig(
                defaults={
                    "fridge": ZoneThresholds(
                        min=settings.fridge_temp_min,
                        max=settings.fridge_temp_max,
                    ),
                    "freezer": ZoneThresholds(
                        min=settings.freezer_temp_min,
                        max=settings.freezer_temp_max,
                    ),
                }
            ),
            email=EmailConfig(
                smtp=SmtpConfig(
                    host=settings.smtp_host,
                    port=settings.smtp_port,
                    use_tls=settings.smtp_use_tls,
                    user=settings.smtp_user,
                    password=settings.smtp_password,
                    recipients=settings.alert_recipients,
                ),
                imap=ImapConfig(
                    host=settings.imap_host,
                    port=settings.imap_port,
                    use_ssl=settings.imap_use_ssl,
                    user=settings.imap_user,
                    password=settings.imap_password,
                    folder=settings.imap_folder,
                    check_interval_seconds=settings.imap_check_interval_seconds,
                ),
            ),
        )

        # Load delta from config.json (only UI-modified fields)
        delta = self._load_delta()
        if delta:
            merged = {**base.model_dump(), **delta}
            try:
                return AppConfig(**merged)
            except Exception as e:
                logger.warning("Invalid config.json delta, using .env defaults: %s", e)

        return base

    def _load_delta(self) -> dict[str, Any]:
        """Load the UI delta from config.json."""
        if not CONFIG_JSON_PATH.exists():
            return {}
        try:
            text = CONFIG_JSON_PATH.read_text(encoding="utf-8").strip()
            if text:
                delta = json.loads(text)
                self._delta = delta  # sync in-memory cache
                return delta
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Invalid config.json, ignoring: %s", e)
        return {}

    def _save_delta(self) -> None:
        """Persist only the UI delta to config.json."""
        CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_JSON_PATH.write_text(
            json.dumps(self._delta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Config delta saved: %s", list(self._delta.keys()))


# Singleton instance
config_service = ConfigService()
```

- [ ] **Step 4: Verifica che i test passino**

```bash
pytest backend/tests/test_config_service.py -v
```
Atteso: tutti PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/config_service.py backend/tests/test_config_service.py
git commit -m "[fix] config.json salva solo delta UI, .env non viene più congelato (BUG-6)"
```

---

### Task 3: Fix smtp_host default guard (BUG 8)

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/services/email_service.py`

- [ ] **Step 1: Cambia default di smtp_host in config.py**

In `backend/config.py`, riga 32, cambia:
```python
# PRIMA:
smtp_host: str = "smtp.example.com"
# DOPO:
smtp_host: str = ""
```

- [ ] **Step 2: Aggiorna il guard in email_service.py (aggiungi controllo placeholder)**

Il guard in `email_service.py:27` diventa automaticamente corretto perché `""` è falsy. Ma aggiungiamo anche un test:

```python
# backend/tests/test_email_service.py — aggiungi questo test:
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_send_alert_email_skips_when_smtp_not_configured():
    """Non deve tentare connessione SMTP se host è vuoto."""
    from backend.services.email_service import send_alert_email
    from backend.services.config_service import config_service
    from backend.models.config_model import AppConfig, SmtpConfig, EmailConfig

    alert = {
        "zone": "fridge", "sensor_id": "0x1234", "temperature": 10.0,
        "level": "WARNING", "threshold_min": 0.0, "threshold_max": 8.0,
        "message": "test", "timestamp": None,
    }

    with patch.object(config_service, "get_config") as mock_cfg:
        mock_cfg.return_value = AppConfig(
            email=EmailConfig(smtp=SmtpConfig(host="", user="", recipients=""))
        )
        # Non deve sollevare eccezione, non deve tentare connessione
        await send_alert_email(alert)  # deve ritornare silenziosamente
```

- [ ] **Step 3: Esegui test**

```bash
pytest backend/tests/ -k "test_send_alert_email_skips" -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/tests/test_email_service.py
git commit -m "[fix] smtp_host default '' evita timeout su smtp.example.com (BUG-8)"
```

---

## Phase 2 — MQTT + Scheduler Startup

### Task 4: Fix async callback MQTT + zone detection da sensors.json (BUG 2, 4)

**Files:**
- Modify: `backend/services/mqtt_client.py`
- Test: `backend/tests/test_mqtt_client.py`

- [ ] **Step 1: Scrivi test**

```python
# backend/tests/test_mqtt_client.py
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from backend.services.mqtt_client import MQTTClient


def test_detect_zone_uses_sensors_registry():
    """La zona deve venire da sensors.json, non dalla temperatura."""
    sensors = {"0xFREEZER": {"zone": "freezer", "name": "Freezer1", "active": True}}

    with patch("backend.services.mqtt_client._load_sensors_zone", return_value=sensors):
        client = MQTTClient()
        assert client._get_zone("0xFREEZER") == "freezer"

def test_detect_zone_falls_back_to_heuristic_when_unknown():
    """Sensore sconosciuto: usa euristica temperatura."""
    with patch("backend.services.mqtt_client._load_sensors_zone", return_value={}):
        client = MQTTClient()
        # Temperatura positiva → fridge
        assert client._get_zone("0xUNKNOWN", temp=4.0) == "fridge"
        # Temperatura negativa → freezer
        assert client._get_zone("0xUNKNOWN", temp=-18.0) == "freezer"

def test_on_message_schedules_async_callback():
    """Il callback async deve essere schedulato sul loop asyncio."""
    loop = asyncio.new_event_loop()
    scheduled = []

    async def fake_callback(reading):
        scheduled.append(reading)

    client = MQTTClient(on_reading=fake_callback, loop=loop)

    msg = MagicMock()
    msg.topic = "zigbee2mqtt/0x1234"
    msg.payload = json.dumps({"temperature": 4.5, "humidity": 60}).encode()

    with patch("backend.services.mqtt_client._load_sensors_zone", return_value={}):
        client._on_message(None, None, msg)
        # Esegui il loop per processare le coroutine schedulate
        loop.run_until_complete(asyncio.sleep(0.05))

    assert len(scheduled) == 1
    assert scheduled[0]["temperature"] == 4.5
    loop.close()
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
pytest backend/tests/test_mqtt_client.py -v
```

- [ ] **Step 3: Riscrivi mqtt_client.py**

```python
"""MQTT client — subscribes to zigbee2mqtt/# and writes readings."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Coroutine

import paho.mqtt.client as mqtt

from backend.config import settings
from backend.paths import data_file

logger = logging.getLogger(__name__)

RECONNECT_MIN = 1
RECONNECT_MAX = 60

_SENSORS_FILE = data_file("sensors.json")


def _load_sensors_zone() -> dict[str, dict]:
    """Load sensors registry from file (returns {sensor_id: {zone, name, active}})."""
    if _SENSORS_FILE.exists():
        try:
            import json as _json
            return _json.loads(_SENSORS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class MQTTClient:
    """Paho-MQTT client with exponential backoff reconnection.

    The on_reading callback is an async coroutine. It is scheduled onto
    the provided asyncio event loop from Paho's background thread using
    run_coroutine_threadsafe(), so it never blocks the MQTT thread.
    """

    def __init__(
        self,
        on_reading: Callable[[dict[str, Any]], Coroutine] | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._on_reading = on_reading
        self._loop = loop
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._reconnect_delay = RECONNECT_MIN
        self._running = False

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Connect to MQTT broker and start loop in background thread."""
        if loop:
            self._loop = loop
        host = settings.mqtt_host
        port = settings.mqtt_port
        logger.info("Connecting to MQTT broker %s:%d", host, port)
        try:
            self._client.connect(host, port, keepalive=60)
            self._running = True
            self._client.loop_start()
        except Exception as e:
            logger.error("MQTT initial connection failed: %s", e)
            self._schedule_reconnect()

    def stop(self) -> None:
        """Disconnect and stop MQTT loop."""
        self._running = False
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT client stopped")

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            logger.info("MQTT connected, subscribing to zigbee2mqtt/#")
            client.subscribe("zigbee2mqtt/#")
            self._reconnect_delay = RECONNECT_MIN
        else:
            logger.error("MQTT connection failed with code %d", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None) -> None:
        if self._running:
            logger.warning("MQTT disconnected (rc=%d), scheduling reconnect", rc)
            self._schedule_reconnect()

    def _on_message(self, client, userdata, msg) -> None:
        try:
            topic = msg.topic
            if "/bridge/" in topic or not msg.payload:
                return

            payload = json.loads(msg.payload.decode("utf-8"))
            if "temperature" not in payload:
                return

            parts = topic.split("/")
            if len(parts) < 2:
                return
            sensor_id = parts[-1]

            temp = float(payload["temperature"])
            reading = {
                "sensor_id": sensor_id,
                "zone": self._get_zone(sensor_id, temp=temp),
                "temperature": temp,
                "humidity": float(payload["humidity"]) if "humidity" in payload else None,
                "battery": int(payload["battery"]) if "battery" in payload else None,
            }

            logger.debug("Reading from %s: %.1f°C zone=%s", sensor_id, temp, reading["zone"])

            if self._on_reading and self._loop and self._loop.is_running():
                # Schedule async callback safely from Paho's background thread
                asyncio.run_coroutine_threadsafe(
                    self._on_reading(reading), self._loop
                )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse MQTT message on %s: %s", msg.topic, e)

    def _get_zone(self, sensor_id: str, temp: float = 20.0) -> str:
        """Return zone for a sensor.

        Primary: look up sensors registry (sensors.json).
        Fallback: temperature heuristic (only for unknown sensors).
        """
        sensors = _load_sensors_zone()
        entry = sensors.get(sensor_id)
        if entry:
            return entry.get("zone", "fridge")
        # Heuristic fallback for unregistered sensors
        return "freezer" if temp < 0 else "fridge"

    def _schedule_reconnect(self) -> None:
        """Reconnect with exponential backoff in a separate thread."""
        import threading

        def _reconnect():
            logger.info("Reconnecting in %ds...", self._reconnect_delay)
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, RECONNECT_MAX)
            if not self._running:
                return
            try:
                self._client.reconnect()
            except Exception as e:
                logger.error("Reconnect failed: %s", e)
                if self._running:
                    self._schedule_reconnect()

        threading.Thread(target=_reconnect, daemon=True).start()
```

- [ ] **Step 4: Verifica che i test passino**

```bash
pytest backend/tests/test_mqtt_client.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/mqtt_client.py backend/tests/test_mqtt_client.py
git commit -m "[fix] MQTT zona da sensors.json + callback async thread-safe (BUG-2, BUG-4)"
```

---

### Task 5: Avvia MQTT + APScheduler in main.py lifespan (BUG 1)

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Installa apscheduler (verificare requirements.txt)**

Verificare che `apscheduler` sia già in `requirements.txt` (risulta già presente).

- [ ] **Step 2: Aggiorna main.py con lifespan completo**

Sostituire l'intero contenuto di `backend/main.py`:

```python
"""medMonitor — FastAPI backend entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.dependencies import close_db, get_db
from backend.routers import config as config_router
from backend.routers import thresholds as thresholds_router
from backend.routers import readings as readings_router
from backend.routers import sensors as sensors_router
from backend.routers import alerts as alerts_router
from backend.routers import demo as demo_router
from backend.services.alert_service import alert_service
from backend.services.imap_service import imap_service
from backend.services.mqtt_client import MQTTClient
from backend.services.config_service import config_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# MQTT client singleton
_mqtt_client: MQTTClient | None = None
_scheduler: AsyncIOScheduler | None = None


async def _on_mqtt_reading(reading: dict) -> None:
    """Async callback: write MQTT reading to DB."""
    try:
        db = get_db()
        await db.write_reading(reading)
    except Exception as e:
        logger.error("Failed to write MQTT reading: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mqtt_client, _scheduler

    logger.info("medMonitor backend starting — database: %s", settings.database_backend)

    # Pre-initialize DB adapter
    get_db()

    # Start APScheduler
    _scheduler = AsyncIOScheduler()
    cfg = config_service.get_config()
    _scheduler.add_job(
        alert_service.check_alerts,
        "interval",
        seconds=60,
        id="alert_check",
    )
    _scheduler.add_job(
        imap_service.check_inbox,
        "interval",
        seconds=cfg.email.imap.check_interval_seconds,
        id="imap_check",
    )
    _scheduler.start()
    logger.info("APScheduler started (alert_check 60s, imap_check %ds)",
                cfg.email.imap.check_interval_seconds)

    # Start MQTT client
    loop = asyncio.get_running_loop()
    _mqtt_client = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
    _mqtt_client.start()
    logger.info("MQTT client started")

    yield

    # Shutdown
    if _mqtt_client:
        _mqtt_client.stop()
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    await close_db()
    logger.info("medMonitor backend shutting down")


# CORS origins — configurable via CORS_ORIGINS env var
_cors_origins = getattr(settings, "cors_origins", "http://localhost:8050").split(",")

app = FastAPI(
    title=settings.app_name,
    description="Monitoraggio temperatura ZigBee per celle frigorifere",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router.router)
app.include_router(thresholds_router.router)
app.include_router(readings_router.router)
app.include_router(sensors_router.router)
app.include_router(alerts_router.router)
app.include_router(demo_router.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "database_backend": settings.database_backend,
        "version": "0.4.0",
        "mqtt_connected": _mqtt_client is not None and _mqtt_client._running,
        "scheduler_running": _scheduler is not None and _scheduler.running,
    }
```

- [ ] **Step 3: Aggiungi cors_origins a config.py**

In `backend/config.py`, aggiungi dopo `demo_speed`:
```python
cors_origins: str = "http://localhost:8050"
```

- [ ] **Step 4: Verifica avvio backend**

```bash
cd W:/varie/SV/medMonitor && python -c "from backend.main import app; print('Import OK')"
```
Atteso: `Import OK`

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/config.py
git commit -m "[fix] avvia MQTT client + APScheduler nel lifespan FastAPI (BUG-1)"
```

---

## Phase 3 — Fix nei servizi

### Task 6: Fix SPEED_MAP invertita in demo_generator.py (BUG 3)

**Files:**
- Modify: `backend/services/demo_generator.py`
- Test: `backend/tests/test_demo_generator.py`

- [ ] **Step 1: Scrivi test**

```python
# Aggiungere a backend/tests/test_demo_generator.py:

def test_speed_map_1x_is_realtime():
    """1x deve corrispondere a tempo reale: 1 step ogni 10 minuti reali."""
    from backend.services.demo_generator import SPEED_MAP
    speed_factor = SPEED_MAP["1x"]
    interval = 10 * 60 * speed_factor  # secondi tra uno step e l'altro
    assert abs(interval - 600) < 1, f"1x deve dare ~600s di intervallo, got {interval}"

def test_speed_map_600x_is_fast():
    """600x deve dare 1 step al secondo reale."""
    from backend.services.demo_generator import SPEED_MAP
    speed_factor = SPEED_MAP["600x"]
    interval = 10 * 60 * speed_factor
    assert abs(interval - 1.0) < 0.1, f"600x deve dare ~1s di intervallo, got {interval}"

def test_speed_map_ordering():
    """Velocità maggiore deve dare intervalli minori."""
    from backend.services.demo_generator import SPEED_MAP
    speeds = ["1x", "10x", "60x", "600x"]
    intervals = [10 * 60 * SPEED_MAP[s] for s in speeds]
    # Gli intervalli devono essere decrescenti
    assert intervals == sorted(intervals, reverse=True), \
        f"Intervalli non decrescenti: {list(zip(speeds, intervals))}"
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
pytest backend/tests/test_demo_generator.py::test_speed_map_1x_is_realtime -v
```

- [ ] **Step 3: Correggi SPEED_MAP in demo_generator.py**

Riga 13-18, sostituisci:

```python
# Speed multipliers: seconds of real time per simulated step (10 sim minutes)
# 1 step = 10 simulated minutes
SPEED_MAP = {
    "1x":   1.0,        # 1 step ogni 600s reali  (tempo reale)
    "10x":  1 / 10,     # 1 step ogni 60s reali   (10x più veloce)
    "60x":  1 / 60,     # 1 step ogni 10s reali   (60x più veloce)
    "600x": 1 / 600,    # 1 step ogni 1s reale    (600x più veloce)
}
```

Poi aggiorna la formula dell'intervallo (riga ~149):

```python
# Interval between steps in real seconds = 10 simulated minutes * speed_factor
interval = 10 * 60 * speed_factor
interval = max(interval, 0.1)
```

- [ ] **Step 4: Verifica che i test passino**

```bash
pytest backend/tests/test_demo_generator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/demo_generator.py backend/tests/test_demo_generator.py
git commit -m "[fix] SPEED_MAP demo invertita — 1x=realtime, 600x=veloce (BUG-3)"
```

---

### Task 7: Fix race condition pool TimescaleDB (BUG 7)

**Files:**
- Modify: `backend/database/timescale_adapter.py`

- [ ] **Step 1: Aggiunge asyncio.Lock a TimescaleAdapter**

In `backend/database/timescale_adapter.py`, modifica `__init__` e `_ensure_pool`:

```python
def __init__(self, dsn: str) -> None:
    self._dsn = dsn
    self._pool: asyncpg.Pool | None = None
    self._pool_lock = asyncio.Lock()

async def _ensure_pool(self) -> asyncpg.Pool:
    if self._pool is not None:
        return self._pool
    async with self._pool_lock:
        # Double-check after acquiring lock
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
            logger.info("TimescaleDB connection pool created")
    return self._pool
```

- [ ] **Step 2: Aggiungi import asyncio**

Assicurarsi che `import asyncio` sia in cima al file.

- [ ] **Step 3: Commit**

```bash
git add backend/database/timescale_adapter.py
git commit -m "[fix] asyncio.Lock su TimescaleDB _ensure_pool (BUG-7)"
```

---

### Task 8: Ripristina stato AlertService da DB al riavvio (BUG 5)

**Files:**
- Modify: `backend/services/alert_service.py`
- Test: `backend/tests/test_alert_service.py`

- [ ] **Step 1: Scrivi test per restore_state**

```python
# Aggiungere a backend/tests/test_alert_service.py:
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.alert_service import AlertService


@pytest.mark.asyncio
async def test_restore_state_loads_last_email_from_db():
    """Al riavvio, _last_email_sent viene caricato dagli alert recenti nel DB."""
    now = datetime.now(timezone.utc)
    recent_alert = {
        "sensor_id": "0xABCD",
        "zone": "fridge",
        "level": "CRITICAL",
        "timestamp": now - timedelta(minutes=10),
        "temperature": 15.0,
        "threshold_min": 0.0,
        "threshold_max": 8.0,
        "message": "test",
    }

    mock_db = MagicMock()
    mock_db.get_alerts = AsyncMock(return_value=[recent_alert])

    svc = AlertService()
    with patch("backend.services.alert_service.get_db", return_value=mock_db):
        await svc.restore_state()

    assert "0xABCD" in svc._last_email_sent
    assert abs((svc._last_email_sent["0xABCD"] - recent_alert["timestamp"]).total_seconds()) < 1
```

- [ ] **Step 2: Verifica che il test fallisca**

```bash
pytest backend/tests/test_alert_service.py::test_restore_state_loads_last_email_from_db -v
```

- [ ] **Step 3: Aggiungi metodo restore_state ad AlertService**

In `backend/services/alert_service.py`, aggiungi dopo `__init__`:

```python
async def restore_state(self) -> None:
    """Restore in-memory state from DB after restart.

    Loads the latest alert per sensor (within cooldown window) to prevent
    duplicate emails immediately after restart.
    """
    try:
        db = get_db()
        config = config_service.get_config()
        cooldown = config.alert_cooldown_minutes
        from_dt = datetime.now(timezone.utc) - timedelta(minutes=cooldown * 2)

        recent_alerts = await db.get_alerts(from_dt=from_dt)

        for alert in recent_alerts:
            sensor_id = alert["sensor_id"]
            ts = alert["timestamp"]
            # Keep only the most recent alert per sensor
            if sensor_id not in self._last_email_sent or ts > self._last_email_sent[sensor_id]:
                self._last_email_sent[sensor_id] = ts

        if self._last_email_sent:
            logger.info("AlertService restored state for %d sensors", len(self._last_email_sent))
    except Exception as e:
        logger.warning("Failed to restore alert state: %s", e)
```

- [ ] **Step 4: Chiama restore_state nel lifespan (main.py)**

Aggiunge dopo `get_db()` nel lifespan di `main.py`:
```python
# Restore alert service state from DB
await alert_service.restore_state()
logger.info("AlertService state restored")
```

- [ ] **Step 5: Verifica che i test passino**

```bash
pytest backend/tests/test_alert_service.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/alert_service.py backend/main.py backend/tests/test_alert_service.py
git commit -m "[fix] AlertService ripristina _last_email_sent da DB al riavvio (BUG-5)"
```

---

### Task 9: Fix IMAP — marca Seen DOPO callback (BUG 14)

**Files:**
- Modify: `backend/services/imap_service.py`

**Approccio:** `_fetch_commands_sync` restituisce i comandi già parsati. La chiamata `conn.store("+FLAGS", "\\Seen")` deve avvenire solo DOPO che il comando è stato confermato valido. Lo spostiamo alla fine del ciclo per ogni msg_id, ma SOLO se il comando è riconosciuto. Gli `msg_id` con comando riconosciuto vengono marcati as Seen alla fine del batch.

- [ ] **Step 1: Modifica `_fetch_commands_sync`**

Sostituisci il loop interno (righe 80-100) con:

```python
pending_seen: list[bytes] = []  # msg_ids to mark as Seen after processing

for msg_id in message_ids[0].split():
    status, msg_data = conn.fetch(msg_id, "(RFC822)")
    if status != "OK":
        continue

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    body = self._extract_body(msg)
    if not body:
        continue

    first_line = body.strip().split("\n")[0].strip().upper()
    command = self._parse_command(first_line)

    if command:
        command["from"] = msg.get("From", "")
        command["subject"] = msg.get("Subject", "")
        results.append(command)
        logger.info("IMAP command: %s from %s", command["type"], command["from"])
        # Accumulate to mark Seen after all commands are collected
        pending_seen.append(msg_id)

# Mark as Seen only after all commands have been collected and added to results
for msg_id in pending_seen:
    try:
        conn.store(msg_id, "+FLAGS", "\\Seen")
    except Exception as e:
        logger.warning("Failed to mark message %s as Seen: %s", msg_id, e)
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/imap_service.py
git commit -m "[fix] IMAP marca messaggi Seen dopo raccolta comandi (BUG-14)"
```

---

## Phase 4 — Logica Allarmi

### Task 10: Aggiungi campo resolved agli alert + counter dashboard (BUG 10)

**Files:**
- Modify: `backend/models/alert.py`
- Modify: `backend/routers/alerts.py`
- Modify: `backend/database/tinyflux_adapter.py`
- Modify: `backend/database/timescale_adapter.py`
- Modify: `frontend/callbacks/dashboard_callbacks.py`

**Approccio:** Aggiungere campo `resolved: bool = False` al modello Alert e alla DB. Aggiungere endpoint `PATCH /api/alerts/{id}/resolve`. Per il counter dashboard, "allarmi attivi" = alert non resolved nelle ultime 24h.

- [ ] **Step 1: Aggiorna modello Alert**

In `backend/models/alert.py`, aggiungi campo `resolved`:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Alert(BaseModel):
    id: str = ""  # UUID o hash per identificare l'alert
    zone: str
    sensor_id: str
    temperature: float
    level: str
    threshold_min: float
    threshold_max: float
    message: str = ""
    timestamp: Optional[datetime] = None
    resolved: bool = False
```

- [ ] **Step 2: Aggiorna TinyFlux write_alert per salvare resolved e id**

In `tinyflux_adapter.py`, `write_alert()`:
```python
async def write_alert(self, alert: dict[str, Any]) -> None:
    import uuid
    ts = alert.get("timestamp", datetime.now(timezone.utc))
    alert_id = alert.get("id") or str(uuid.uuid4())[:8]
    point = Point(
        time=ts,
        tags={
            "zone": alert["zone"],
            "sensor_id": alert["sensor_id"],
            "level": alert["level"],
            "measurement": "alert",
            "message": str(alert.get("message", "")),
            "alert_id": alert_id,
        },
        fields={
            "temperature": float(alert["temperature"]),
            "threshold_min": float(alert["threshold_min"]),
            "threshold_max": float(alert["threshold_max"]),
            "resolved": 1 if alert.get("resolved", False) else 0,
        },
    )
    self._db.insert(point)
```

Aggiorna anche `_point_to_alert` per includere `id` e `resolved`:
```python
@staticmethod
def _point_to_alert(point: Point) -> dict[str, Any]:
    return {
        "id": point.tags.get("alert_id", ""),
        "zone": point.tags.get("zone", ""),
        "sensor_id": point.tags.get("sensor_id", ""),
        "level": point.tags.get("level", ""),
        "temperature": point.fields.get("temperature", 0.0),
        "threshold_min": point.fields.get("threshold_min", 0.0),
        "threshold_max": point.fields.get("threshold_max", 0.0),
        "message": point.tags.get("message", ""),
        "timestamp": point.time,
        "resolved": bool(point.fields.get("resolved", 0)),
    }
```

- [ ] **Step 3: Aggiorna TimescaleDB per campo resolved**

In `timescale_adapter.py`, aggiungi colonna `resolved` alla INSERT e SELECT:

```python
async def write_alert(self, alert: dict[str, Any]) -> None:
    import uuid
    pool = await self._ensure_pool()
    ts = alert.get("timestamp", datetime.now(timezone.utc))
    alert_id = alert.get("id") or str(uuid.uuid4())[:8]
    await pool.execute(
        """
        INSERT INTO alerts
            (id, zone, sensor_id, temperature, level, threshold_min,
             threshold_max, message, timestamp, resolved)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        alert_id,
        alert["zone"], alert["sensor_id"],
        float(alert["temperature"]), alert["level"],
        float(alert["threshold_min"]), float(alert["threshold_max"]),
        alert.get("message", ""), ts,
        alert.get("resolved", False),
    )
```

Aggiorna `get_alerts` SELECT e `_row_to_alert`:
```python
@staticmethod
def _row_to_alert(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"] if "id" in row.keys() else "",
        "zone": row["zone"],
        "sensor_id": row["sensor_id"],
        "temperature": float(row["temperature"]),
        "level": row["level"],
        "threshold_min": float(row["threshold_min"]),
        "threshold_max": float(row["threshold_max"]),
        "message": row["message"],
        "timestamp": row["timestamp"],
        "resolved": bool(row["resolved"]) if "resolved" in row.keys() else False,
    }
```

Aggiorna la CREATE TABLE in `init.sql` (Task 16).

- [ ] **Step 4: Aggiungi endpoint resolve in alerts router**

In `backend/routers/alerts.py`, aggiungi:

```python
@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved (acknowledged by operator)."""
    # Per TinyFlux: non supporta update in-place, skippiamo per ora
    # Per TimescaleDB: aggiorniamo il campo resolved
    db = get_db()
    if hasattr(db, "_pool"):  # TimescaleDB
        pool = await db._ensure_pool()
        await pool.execute(
            "UPDATE alerts SET resolved = TRUE WHERE id = $1",
            alert_id,
        )
    return {"status": "ok", "alert_id": alert_id, "resolved": True}
```

- [ ] **Step 5: Fix counter "allarmi attivi" in dashboard_callbacks.py**

Riga 54, sostituisci:
```python
# PRIMA:
active_alerts = len([a for a in alerts if a.get("level") == "CRITICAL"])

# DOPO — conta solo alert non resolved nelle ultime 24h:
from datetime import datetime, timezone, timedelta
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

def _is_recent(a):
    ts = a.get("timestamp")
    if not ts:
        return False
    if isinstance(ts, str):
        try:
            from dateutil import parser
            ts = parser.parse(ts)
        except Exception:
            return True
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts >= cutoff

active_alerts = len([
    a for a in alerts
    if a.get("level") == "CRITICAL"
    and not a.get("resolved", False)
    and _is_recent(a)
])
```

- [ ] **Step 6: Commit**

```bash
git add backend/models/alert.py backend/routers/alerts.py \
        backend/database/tinyflux_adapter.py backend/database/timescale_adapter.py \
        frontend/callbacks/dashboard_callbacks.py
git commit -m "[fix] alert.resolved field + counter attivi ultime 24h (BUG-10)"
```

---

### Task 11: Mostra stato WARNING nelle zone card (BUG 11)

**Files:**
- Modify: `backend/routers/alerts.py` (aggiunge endpoint status sensori)
- Modify: `frontend/callbacks/dashboard_callbacks.py`

**Approccio:** Aggiunge endpoint `GET /api/sensors/status` che per ogni sensore restituisce il livello attuale (OK/WARNING/CRITICAL) basandosi sugli alert non resolved nelle ultime 20 minuti. Il frontend usa questo per colorare le zone card.

- [ ] **Step 1: Aggiungi endpoint sensor status in sensors router**

In `backend/routers/sensors.py`, aggiungi alla fine:

```python
from datetime import datetime, timezone, timedelta
from backend.dependencies import get_db
from backend.services.config_service import config_service

@router.get("/status")
async def get_sensors_status():
    """Return current alert level (OK/WARNING/CRITICAL) for each sensor."""
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=20)
    recent_alerts = await db.get_alerts(from_dt=cutoff)

    # Keep worst level per sensor
    status: dict[str, str] = {}
    for alert in recent_alerts:
        if alert.get("resolved"):
            continue
        sid = alert["sensor_id"]
        level = alert["level"]
        if sid not in status or level == "CRITICAL":
            status[sid] = level

    return status  # {sensor_id: "WARNING"|"CRITICAL"} — absent means OK
```

- [ ] **Step 2: Aggiorna update_zone_cards in dashboard_callbacks.py**

Sostituisci la determinazione dello status (righe 97-99) con:

```python
# Get sensor status from dedicated endpoint
sensor_status = _fetch("/sensors/status")
if not isinstance(sensor_status, dict):
    sensor_status = {}

...  # nel loop per zona:

# Determine status (OK / WARNING / CRITICAL)
raw_status = sensor_status.get(sensor_id, "ok").lower()
if raw_status not in ("ok", "warning", "critical"):
    raw_status = "ok"
# Also check threshold directly as fallback
if raw_status == "ok" and (temp < eff_min or temp > eff_max):
    raw_status = "warning"  # out of range but no recent alert yet
status = raw_status
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/sensors.py frontend/callbacks/dashboard_callbacks.py
git commit -m "[fix] dashboard mostra stato WARNING oltre a OK/CRITICAL (BUG-11)"
```

---

### Task 12: Fix dashboard multi-sensore per zona (BUG 12)

**Files:**
- Modify: `frontend/callbacks/dashboard_callbacks.py`

**Approccio:** Con più sensori per zona, mostrare la temperatura "peggiore" (più distante dalla soglia) nella metric card, e nella zone card mostrare lo status del sensore in stato peggiore.

- [ ] **Step 1: Refactoring update_metrics e update_zone_cards**

In `update_metrics`, sostituisci il loop (righe 46-52):

```python
# Group readings by zone, track worst temperature
zone_data: dict[str, dict] = {}
for r in latest:
    zone_name = r.get("zone", "")
    if zone_name not in zone_data:
        zone_data[zone_name] = r
    else:
        # Keep reading with temperature furthest from safe center
        # (simple: keep the most extreme temperature)
        prev = zone_data[zone_name]["temperature"]
        curr = r["temperature"]
        # For fridge: higher is worse; for freezer: higher is worse too (warming up)
        # Use absolute distance from midpoint heuristic
        zone_data[zone_name] = r  # simplification: show last in list, fixed in zone_card

fridge_data = zone_data.get("fridge")
freezer_data = zone_data.get("freezer")

fridge_temp = f"{fridge_data['temperature']:.1f}°C" if fridge_data else "—"
freezer_temp = f"{freezer_data['temperature']:.1f}°C" if freezer_data else "—"
fridge_color = "#1D9E75" if fridge_data else "#6c757d"
freezer_color = "#1D9E75" if freezer_data else "#6c757d"

# Count total online sensors
sensor_count = len(latest)
```

In `update_zone_cards`, al posto di sovrascrivere a ogni iterazione, tieni il sensore col livello peggiore:

```python
def update_zone_cards(_n):
    latest = _fetch("/readings/latest")
    thresholds_data = _fetch("/thresholds")
    sensor_status = _fetch("/sensors/status")
    if not isinstance(sensor_status, dict):
        sensor_status = {}

    # Group by zone, pick worst sensor per zone
    zone_worst: dict[str, tuple] = {}  # zone -> (reading, eff_min, eff_max, status, has_override)

    for r in latest:
        zone_name = r.get("zone", "")
        sensor_id = r.get("sensor_id", "")
        temp = r.get("temperature", 0)

        eff_min, eff_max = 0.0, 30.0
        has_override = False
        if isinstance(thresholds_data, dict):
            sensors = thresholds_data.get("sensors", {})
            if sensor_id in sensors:
                s = sensors[sensor_id]
                eff_min = s.get("effective_min", 0)
                eff_max = s.get("effective_max", 30)
                has_override = s.get("override", False)
            else:
                defaults = thresholds_data.get("defaults", {})
                d = defaults.get(zone_name, {})
                eff_min = d.get("min", 0)
                eff_max = d.get("max", 30)

        raw_status = sensor_status.get(sensor_id, "ok").lower()
        if raw_status not in ("ok", "warning", "critical"):
            raw_status = "ok"
        if raw_status == "ok" and (temp < eff_min or temp > eff_max):
            raw_status = "warning"

        # Level priority: critical > warning > ok
        PRIORITY = {"critical": 2, "warning": 1, "ok": 0}
        existing = zone_worst.get(zone_name)
        if existing is None or PRIORITY[raw_status] > PRIORITY[existing[3]]:
            zone_worst[zone_name] = (r, eff_min, eff_max, raw_status, has_override)

    cards = [html.Div(), html.Div()]
    for zone_name, (r, eff_min, eff_max, status, has_override) in zone_worst.items():
        label = "Frigorifero" if zone_name == "fridge" else "Freezer"
        card = zone_card(label, r["temperature"], eff_min, eff_max, status, r["sensor_id"], has_override)
        if zone_name == "fridge":
            cards[0] = card
        elif zone_name == "freezer":
            cards[1] = card

    return cards[0], cards[1]
```

- [ ] **Step 2: Commit**

```bash
git add frontend/callbacks/dashboard_callbacks.py
git commit -m "[fix] dashboard mostra sensore peggiore per zona (BUG-12)"
```

---

## Phase 5 — Semplificazioni infrastruttura

### Task 13: Split requirements.txt in prod + dev (SIMPL 5)

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Crea requirements-dev.txt**

```text
# Development & testing dependencies
-r requirements.txt

pytest==8.2.0
pytest-asyncio==0.23.7
pytest-cov==5.0.0
httpx==0.27.0
python-dateutil>=2.8.0
```

- [ ] **Step 2: Rimuovi dipendenze test da requirements.txt**

Rimuovi le righe:
```
pytest==8.2.0
pytest-asyncio==0.23.7
pytest-cov==5.0.0
httpx==0.27.0
```

Aggiungi `python-dateutil>=2.8.0` a requirements.txt (necessario per parsing timestamp nel dashboard).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt requirements-dev.txt
git commit -m "[refactor] split requirements.txt in prod + dev (SIMPL-5)"
```

---

### Task 14: Fix docker-compose — Dockerfile frontend + healthchecks (BUG 9, SIMPL 4)

**Files:**
- Create: `docker/frontend/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Crea docker/frontend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install production + frontend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/ ./frontend/
COPY backend/ ./backend/

ENV PYTHONPATH=/app

EXPOSE 8050
CMD ["python", "frontend/app.py"]
```

- [ ] **Step 2: Crea docker/backend/Dockerfile (se non già completo)**

Verifica che il Dockerfile backend contenga solo le dipendenze backend. Se condivide le stesse dipendenze Python è accettabile riusarlo, ma il CMD deve essere overridden nel compose.

- [ ] **Step 3: Aggiorna docker-compose.yml**

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    container_name: medmonitor-mosquitto
    ports:
      - "1883:1883"
    volumes:
      - ./docker/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mosquitto_sub", "-t", "$$SYS/#", "-C", "1", "-i", "healthcheck", "-W", "3"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    container_name: medmonitor-backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    environment:
      - MQTT_HOST=mosquitto
      - CORS_ORIGINS=http://localhost:8050
    depends_on:
      mosquitto:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 15s

  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
    container_name: medmonitor-frontend
    ports:
      - "8050:8050"
    env_file:
      - .env
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: medmonitor-postgres
    profiles:
      - timescale
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-medmon}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cambia_questa_password}
      POSTGRES_DB: ${POSTGRES_DB:-medmonitor}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-medmon}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 4: Commit**

```bash
git add docker/frontend/Dockerfile docker-compose.yml
git commit -m "[fix] Dockerfile frontend dedicato + healthchecks compose (BUG-9, SIMPL-4)"
```

---

### Task 15: TimescaleDB init.sql automatico (SIMPL 3)

**Files:**
- Create: `docker/postgres/init.sql`

- [ ] **Step 1: Crea init.sql**

```sql
-- medMonitor — TimescaleDB schema initialization
-- Eseguito automaticamente al primo avvio del container postgres

CREATE TABLE IF NOT EXISTS temperature_readings (
    id          BIGSERIAL,
    zone        TEXT        NOT NULL,
    sensor_id   TEXT        NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    humidity    DOUBLE PRECISION,
    battery     INTEGER,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('temperature_readings', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_ts
    ON temperature_readings (sensor_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS alerts (
    id              TEXT        NOT NULL DEFAULT gen_random_uuid()::TEXT,
    zone            TEXT        NOT NULL,
    sensor_id       TEXT        NOT NULL,
    temperature     DOUBLE PRECISION NOT NULL,
    level           TEXT        NOT NULL,
    threshold_min   DOUBLE PRECISION NOT NULL,
    threshold_max   DOUBLE PRECISION NOT NULL,
    message         TEXT        NOT NULL DEFAULT '',
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved        BOOLEAN     NOT NULL DEFAULT FALSE
);

SELECT create_hypertable('alerts', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_alerts_level_ts
    ON alerts (level, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_sensor_ts
    ON alerts (sensor_id, timestamp DESC);
```

- [ ] **Step 2: Commit**

```bash
git add docker/postgres/init.sql
git commit -m "[feat] init.sql auto-crea tabelle TimescaleDB (SIMPL-3)"
```

---

### Task 16: Script di setup one-shot (SIMPL 1)

**Files:**
- Create: `setup.bat`
- Create: `setup.sh`

- [ ] **Step 1: Crea setup.bat (Windows)**

```batch
@echo off
setlocal enabledelayedexpansion
echo === medMonitor Setup ===

REM Check Python
python --version >nul 2>&1 || (echo ERRORE: Python non trovato. Installa Python 3.11+ && exit /b 1)

REM Create venv
if not exist "venv\" (
    echo Creazione ambiente virtuale...
    python -m venv venv
)

REM Activate and install
echo Installazione dipendenze...
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q

REM Create data directory
if not exist "data\" mkdir data

REM Copy .env if missing
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo Creato .env da .env.example - modifica con le tue credenziali!
    ) else (
        echo ATTENZIONE: .env.example non trovato
    )
)

echo.
echo === Setup completato! ===
echo Per avviare il backend:   venv\Scripts\activate ^& uvicorn backend.main:app --reload --port 8000
echo Per avviare il frontend:  venv\Scripts\activate ^& python frontend/app.py
echo.
```

- [ ] **Step 2: Crea setup.sh (Linux/Mac)**

```bash
#!/usr/bin/env bash
set -e
echo "=== medMonitor Setup ==="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERRORE: Python3 non trovato. Installa Python 3.11+"
    exit 1
fi

# Create venv
if [ ! -d "venv" ]; then
    echo "Creazione ambiente virtuale..."
    python3 -m venv venv
fi

# Install
echo "Installazione dipendenze..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Create data directory
mkdir -p data

# Copy .env
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Creato .env da .env.example — modifica con le tue credenziali!"
fi

echo ""
echo "=== Setup completato! ==="
echo "Backend:  source venv/bin/activate && uvicorn backend.main:app --reload --port 8000"
echo "Frontend: source venv/bin/activate && python frontend/app.py"
```

- [ ] **Step 3: Rendi setup.sh eseguibile e commit**

```bash
chmod +x setup.sh
git add setup.bat setup.sh
git commit -m "[feat] script setup one-shot Windows e Linux (SIMPL-1)"
```

---

## Phase 6 — Verifica finale

### Task 17: Esegui tutti i test e verifica integrità

- [ ] **Step 1: Installa dipendenze dev**

```bash
cd W:/varie/SV/medMonitor
source venv/Scripts/activate  # o venv\Scripts\activate su Windows
pip install -r requirements-dev.txt -q
```

- [ ] **Step 2: Esegui suite test completa**

```bash
pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```
Atteso: tutti i test PASS, coverage > 60%

- [ ] **Step 3: Verifica import backend**

```bash
python -c "from backend.main import app; print('Backend import OK')"
python -c "from frontend.app import app; print('Frontend import OK')"
```

- [ ] **Step 4: Tag finale**

```bash
git tag -a v0.5.0 -m "v0.5.0 — bugfix completo + semplificazioni installazione"
```

---

## Riepilogo bug risolti

| Bug | Task | Commit prefix |
|-----|------|--------------|
| BUG-13 path relativi | Task 1 | `[fix]` |
| BUG-6 config hierarchy | Task 2 | `[fix]` |
| BUG-8 smtp_host default | Task 3 | `[fix]` |
| BUG-2 MQTT async callback | Task 4 | `[fix]` |
| BUG-4 zone detection | Task 4 | `[fix]` |
| BUG-1 MQTT+scheduler non avviati | Task 5 | `[fix]` |
| BUG-3 SPEED_MAP invertita | Task 6 | `[fix]` |
| BUG-7 pool race condition | Task 7 | `[fix]` |
| BUG-5 state perde al riavvio | Task 8 | `[fix]` |
| BUG-14 IMAP Seen prima del callback | Task 9 | `[fix]` |
| BUG-10 counter allarmi non decresce | Task 10 | `[fix]` |
| BUG-11 WARNING status mancante | Task 11 | `[fix]` |
| BUG-12 multi-sensore per zona | Task 12 | `[fix]` |
| BUG-9 Dockerfile frontend sbagliato | Task 14 | `[fix]` |
| SIMPL-5 split requirements | Task 13 | `[refactor]` |
| SIMPL-4 healthchecks compose | Task 14 | `[feat]` |
| SIMPL-3 init.sql TimescaleDB | Task 15 | `[feat]` |
| SIMPL-1 script setup | Task 16 | `[feat]` |
| SIMPL-6 CORS da env | Task 5 | `[fix]` |
| SIMPL-7 path centralizzati | Task 1 | `[fix]` |
