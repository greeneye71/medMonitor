# medMonitor v2 — UI Redesign + Robustezza — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sostituire l'UI SLATE dark con un design Modern SaaS Light, aggiungere la pagina Sistema per monitoraggio/controllo servizi backend, completare la configurazione sensori con auto-discovery, aumentare la robustezza frontend+backend, e implementare archiviazione automatica dei dati a CSV dopo 180 giorni.

**Architecture:** Frontend Plotly Dash con Bootstrap FLATLY (light), sidebar fissa 220px, 5 pagine (Dashboard/Storico/Allarmi/Impostazioni/Sistema). Backend FastAPI con nuovi router (health, logs, archive, zone API estesa) e `app.state` per stato servizi condiviso.

**Tech Stack:** Python 3.11, FastAPI, Plotly Dash, Dash Bootstrap Components (FLATLY), Dash-AG-Grid (ag-theme-quartz), APScheduler, Paho-MQTT, TinyFlux/TimescaleDB, CSV stdlib.

---

## File Structure

### Nuovi file da creare
- `frontend/assets/custom.css` — variabili CSS palette, card, badge, sidebar
- `frontend/pages/system.py` — layout pagina Sistema
- `frontend/callbacks/system_callbacks.py` — health polling, service controls, logs
- `frontend/components/zone_card.py` — zone card v2 (border-left, glow CRITICAL)
- `frontend/components/sensors_table.py` — tabella sensori compatta
- `frontend/components/service_status.py` — card servizio con dot + pulsanti
- `frontend/components/log_panel.py` — terminale log scuro
- `frontend/utils.py` — safe_get/safe_post helpers centralizzati
- `backend/routers/health.py` — GET /api/health, POST /services/{name}/{action}
- `backend/routers/logs.py` — GET /api/logs
- `backend/routers/archive.py` — GET /api/archive/status, POST /api/archive/run
- `backend/services/log_collector.py` — LogCollectorHandler + deque
- `backend/services/archive_service.py` — export CSV + delete DB

### File da modificare
- `frontend/app.py` — FLATLY theme, /sistema routing, system_callbacks import
- `frontend/layout.py` — sidebar 220px, Sistema nav, status dots, interval-5s
- `frontend/pages/dashboard.py` — zone cards dinamiche, sensors table, light theme
- `frontend/pages/history.py` — statistiche % fuori soglia, light theme
- `frontend/pages/alerts.py` — ag-theme-quartz, row coloring
- `frontend/pages/settings.py` — 5 tab, sensor discovery, add/delete zona
- `frontend/callbacks/dashboard_callbacks.py` — zone dinamiche, resilienza
- `frontend/callbacks/history_callbacks.py` — % fuori soglia
- `frontend/callbacks/alerts_callbacks.py` — row styling, ag-theme-quartz
- `frontend/callbacks/settings_callbacks.py` — sensor discovery, add zone
- `backend/main.py` — app.state migration, LogCollector, archive job, register routers
- `backend/models/config_model.py` — zone_colors, ThresholdDefaultsPatch generico, archive_after_days
- `backend/services/config_service.py` — update_zone_color, delete_zone_color
- `backend/services/mqtt_client.py` — health_state, discovered_sensors set
- `backend/database/adapter.py` — get_size_mb(), delete_readings_before(), delete_alerts_before()
- `backend/database/tinyflux_adapter.py` — implementa i 3 nuovi metodi
- `backend/database/timescale_adapter.py` — implementa i 3 nuovi metodi (se presente)
- `backend/routers/sensors.py` — GET /discovered, POST /{id}/accept, DELETE /{id}
- `backend/routers/config.py` — GET/POST/DELETE /api/zones
- `backend/routers/thresholds.py` — aggiorna per ThresholdDefaultsPatch.zones

---

## Task 0: Prerequisites

**Files:**
- Modify: `frontend/app.py` (già modificato, non committed)
- Modify: `requirements.txt` (già modificato, non committed)

- [ ] **Step 1: Commit le modifiche pendenti sul branch corrente**

```bash
git add frontend/app.py requirements.txt frontend/__init__.py
git commit -m "[fix] commit modifiche pendenti pre-redesign"
```

- [ ] **Step 2: Creare branch feature/ui-redesign-v2**

```bash
git checkout -b feature/ui-redesign-v2
```

- [ ] **Step 3: Verificare stato pulito**

```bash
git status
```
Expected: `nothing to commit, working tree clean`

---

## Task 1: Design System

**Files:**
- Create: `frontend/assets/custom.css`
- Modify: `frontend/app.py`

- [ ] **Step 1: Creare `frontend/assets/custom.css`**

```css
/* medMonitor v2 — Design System */
:root {
  --mm-bg:          #f8fafc;
  --mm-surface:     #ffffff;
  --mm-sidebar:     #0f172a;
  --mm-sidebar-hover: #1e293b;
  --mm-text:        #0f172a;
  --mm-text-muted:  #64748b;
  --mm-text-faint:  #94a3b8;
  --mm-ok:          #22c55e;
  --mm-warn:        #f59e0b;
  --mm-critical:    #ef4444;
  --mm-info:        #3b82f6;
  --mm-border:      #e2e8f0;
  --mm-radius:      12px;
  --mm-shadow:      0 1px 3px rgba(0,0,0,0.06);
}

body {
  background: var(--mm-bg) !important;
  font-family: system-ui, -apple-system, sans-serif;
}

/* Card base */
.mm-card {
  background: var(--mm-surface);
  border-radius: var(--mm-radius);
  box-shadow: var(--mm-shadow);
  padding: 16px;
  border: 1px solid var(--mm-border);
}

/* Zone card stato */
.mm-card-ok     { border-left: 4px solid var(--mm-ok) !important; }
.mm-card-warn   { border-left: 4px solid var(--mm-warn) !important; }
.mm-card-critical {
  border-left: 4px solid var(--mm-critical) !important;
  box-shadow: 0 0 0 2px rgba(239,68,68,0.15), var(--mm-shadow) !important;
}

/* Badge stato */
.mm-badge-ok       { background: #dcfce7; color: #166534; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
.mm-badge-warn     { background: #fef3c7; color: #92400e; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
.mm-badge-critical { background: #fee2e2; color: #991b1b; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
.mm-badge-info     { background: #dbeafe; color: #1e40af; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }
.mm-badge-new      { background: #f3e8ff; color: #7e22ce; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600; }

/* Sidebar */
.mm-sidebar {
  width: 220px;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  background: var(--mm-sidebar);
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow-y: auto;
}

.mm-sidebar-brand {
  padding: 16px;
  font-size: 14px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.3px;
}

.mm-nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin: 2px 8px;
  border-radius: 6px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.mm-nav-item:hover {
  background: var(--mm-sidebar-hover);
  color: #fff;
  text-decoration: none;
}

.mm-nav-item.active {
  background: var(--mm-sidebar-hover);
  color: #fff;
}

/* Service status dots */
.mm-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.mm-dot-ok       { background: var(--mm-ok); }
.mm-dot-warn     { background: var(--mm-warn); }
.mm-dot-error    { background: var(--mm-critical); }

/* Log panel */
.mm-log-panel {
  background: #0f172a;
  border-radius: 8px;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  height: 400px;
  overflow-y: auto;
  color: #94a3b8;
}

.mm-log-info    { color: #94a3b8; }
.mm-log-warning { color: #f59e0b; }
.mm-log-error   { color: #ef4444; }

/* Page header */
.mm-page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.mm-page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--mm-text);
}

/* Main content */
.mm-main {
  margin-left: 220px;
  background: var(--mm-bg);
  min-height: 100vh;
  padding: 24px;
}

/* Temperature display */
.mm-temp-ok       { color: #15803d; }
.mm-temp-warn     { color: #b45309; }
.mm-temp-critical { color: #dc2626; }
```

- [ ] **Step 2: Aggiornare `frontend/app.py` — FLATLY theme, version 2.0.0**

Cambiare riga 20 da `dbc.themes.SLATE` a `dbc.themes.FLATLY`:

```python
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, "/assets/custom.css"],
    title="medMonitor",
    update_title="medMonitor — Aggiornamento...",
    suppress_callback_exceptions=True,
)
```

- [ ] **Step 3: Verificare che il frontend si avvii senza errori**

```bash
python frontend/app.py
```
Expected: `Dash is running on http://0.0.0.0:8050/` senza traceback

- [ ] **Step 4: Commit**

```bash
git add frontend/assets/custom.css frontend/app.py
git commit -m "[feat] design system v2: custom.css variabili + FLATLY theme"
```

---

## Task 2: Nuovo Layout (Sidebar + Routing)

**Files:**
- Modify: `frontend/layout.py`
- Modify: `frontend/app.py`

- [ ] **Step 1: Riscrivere `frontend/layout.py`**

```python
"""medMonitor v2 — Main layout con sidebar SaaS light."""

from dash import html, dcc
import dash_bootstrap_components as dbc

NAV_ITEMS = [
    {"label": "Dashboard",    "href": "/",             "icon": "📊"},
    {"label": "Storico",      "href": "/storico",      "icon": "📅"},
    {"label": "Allarmi",      "href": "/allarmi",      "icon": "🔔"},
    {"label": "Impostazioni", "href": "/impostazioni", "icon": "⚙️"},
    {"label": "Sistema",      "href": "/sistema",      "icon": "🖥️"},
]


def _nav_item(label: str, href: str, icon: str) -> html.A:
    extra = []
    if label == "Allarmi":
        extra = [
            html.Span(
                "0",
                id="sidebar-alert-badge",
                style={
                    "background": "#ef4444",
                    "color": "#fff",
                    "borderRadius": "10px",
                    "padding": "0 6px",
                    "fontSize": "10px",
                    "fontWeight": "700",
                    "display": "none",
                },
            )
        ]
    return html.A(
        [html.Span(icon, style={"marginRight": "8px"}), label] + extra,
        href=href,
        id=f"nav-{href.strip('/') or 'dashboard'}",
        className="mm-nav-item",
    )


def make_sidebar() -> html.Div:
    return html.Div(
        [
            html.Div("medMonitor", className="mm-sidebar-brand"),
            html.Hr(style={"borderColor": "#1e293b", "margin": "0 0 8px"}),
            html.Div(
                [_nav_item(i["label"], i["href"], i["icon"]) for i in NAV_ITEMS],
                style={"flex": 1},
            ),
            html.Div(
                [
                    html.Hr(style={"borderColor": "#1e293b", "margin": "8px 0"}),
                    html.Div(
                        [
                            html.Span(
                                "",
                                id="dot-mqtt",
                                className="mm-status-dot mm-dot-ok",
                                title="MQTT",
                                style={"marginRight": "4px"},
                            ),
                            html.Span(
                                "",
                                id="dot-scheduler",
                                className="mm-status-dot mm-dot-ok",
                                title="Scheduler",
                                style={"marginRight": "4px"},
                            ),
                            html.Span(
                                "",
                                id="dot-db",
                                className="mm-status-dot mm-dot-ok",
                                title="Database",
                            ),
                        ],
                        style={
                            "padding": "8px 16px 12px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                ]
            ),
        ],
        className="mm-sidebar",
    )


def make_layout() -> html.Div:
    return html.Div(
        [
            make_sidebar(),
            html.Div(
                [
                    dcc.Location(id="url", refresh=False),
                    html.Div(id="demo-banner-container"),
                    html.Div(id="page-content"),
                ],
                className="mm-main",
            ),
            # Intervals — globali, sempre attivi
            dcc.Interval(id="interval-5s",  interval=5_000,  n_intervals=0),
            dcc.Interval(id="interval-30s", interval=30_000, n_intervals=0),
            dcc.Interval(id="interval-60s", interval=60_000, n_intervals=0),
        ]
    )
```

- [ ] **Step 2: Aggiornare `frontend/app.py` — routing /sistema + import system_callbacks**

```python
"""medMonitor — Plotly Dash frontend entry point."""

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import dash
import dash_bootstrap_components as dbc
from dash import html, Input, Output, callback

from frontend.layout import make_layout

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="medMonitor",
    update_title="medMonitor — Aggiornamento...",
    suppress_callback_exceptions=True,
)

server = app.server
app.layout = make_layout()

# Import callbacks to register them
import frontend.callbacks.dashboard_callbacks   # noqa: F401
import frontend.callbacks.history_callbacks     # noqa: F401
import frontend.callbacks.alerts_callbacks      # noqa: F401
import frontend.callbacks.settings_callbacks    # noqa: F401
import frontend.callbacks.system_callbacks      # noqa: F401


@callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    if pathname == "/" or pathname is None:
        from frontend.pages.dashboard import layout
        return layout()
    elif pathname == "/storico":
        from frontend.pages.history import layout
        return layout()
    elif pathname == "/allarmi":
        from frontend.pages.alerts import layout
        return layout()
    elif pathname == "/impostazioni":
        from frontend.pages.settings import layout
        return layout()
    elif pathname == "/sistema":
        from frontend.pages.system import layout
        return layout()
    else:
        return html.Div(
            [
                html.H4("404 — Pagina non trovata"),
                html.P(f"Il percorso '{pathname}' non esiste."),
            ],
            style={"textAlign": "center", "marginTop": "80px"},
        )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
```

- [ ] **Step 3: Creare stub `frontend/callbacks/system_callbacks.py`** (evita ImportError)

```python
"""System page callbacks — stub iniziale."""
# Implementato in Task 7
```

- [ ] **Step 4: Creare stub `frontend/pages/system.py`**

```python
"""Pagina Sistema — stub iniziale."""
from dash import html

def layout():
    return html.Div("Sistema — in costruzione", className="mm-main")
```

- [ ] **Step 5: Verificare avvio e navigazione**

```bash
python frontend/app.py
```
Aprire http://localhost:8050/ e verificare:
- Sidebar dark sinistra 220px visibile
- 5 voci nav con icone
- Navigazione a /sistema mostra "in costruzione"
- 3 dots verdi in fondo alla sidebar

- [ ] **Step 6: Commit**

```bash
git add frontend/layout.py frontend/app.py frontend/pages/system.py frontend/callbacks/system_callbacks.py
git commit -m "[feat] layout v2: sidebar 220px, Sistema nav, status dots, interval-5s"
```

---

## Task 3: Backend Data Model

**Files:**
- Modify: `backend/models/config_model.py`
- Modify: `backend/services/config_service.py`
- Modify: `backend/database/adapter.py`
- Modify: `backend/database/tinyflux_adapter.py`
- Modify: `backend/database/timescale_adapter.py` (se esiste)

- [ ] **Step 1: Scrivere il test**

Creare/aggiornare `backend/tests/test_config_model.py`:

```python
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
```

- [ ] **Step 2: Eseguire il test — deve fallire**

```bash
pytest backend/tests/test_config_model.py -v
```
Expected: FAIL (zone_colors, archive_after_days, zones non esistono)

- [ ] **Step 3: Aggiornare `backend/models/config_model.py`**

```python
class AppConfig(BaseModel):
    """Runtime application configuration (stored in config.json)."""
    app_name: str = "medMonitor"
    app_theme: str = "slate"
    log_level: str = "INFO"
    polling_interval_minutes: int = 10
    alert_cooldown_minutes: int = 30
    data_retention_days: int = 365
    archive_after_days: int = 180
    database_backend: str = "tinyflux"
    zone_colors: dict[str, str] = Field(
        default_factory=lambda: {"fridge": "#22c55e", "freezer": "#3b82f6"}
    )
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)


class ThresholdDefaultsPatch(BaseModel):
    """Update zone default thresholds — generico per zone arbitrarie."""
    zones: dict[str, ZoneThresholds] | None = None
```

Nota: se il router `thresholds.py` usa `patch.fridge`/`patch.freezer`, va aggiornato nel Task 5.

- [ ] **Step 4: Eseguire il test — deve passare**

```bash
pytest backend/tests/test_config_model.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Scrivere test per ConfigService zone_color**

In `backend/tests/test_config_service.py` aggiungere:

```python
def test_update_zone_color(tmp_path, monkeypatch):
    from backend.services.config_service import ConfigService
    monkeypatch.setattr("backend.paths.DATA_DIR", tmp_path)
    svc = ConfigService()
    svc.update_zone_color("cold_room", "#a855f7")
    cfg = svc.get_config()
    assert cfg.zone_colors.get("cold_room") == "#a855f7"


def test_delete_zone_color(tmp_path, monkeypatch):
    from backend.services.config_service import ConfigService
    monkeypatch.setattr("backend.paths.DATA_DIR", tmp_path)
    svc = ConfigService()
    svc.update_zone_color("cold_room", "#a855f7")
    svc.delete_zone_color("cold_room")
    cfg = svc.get_config()
    assert "cold_room" not in cfg.zone_colors
```

- [ ] **Step 6: Eseguire il test — deve fallire**

```bash
pytest backend/tests/test_config_service.py::test_update_zone_color -v
```
Expected: FAIL (`ConfigService` has no attribute `update_zone_color`)

- [ ] **Step 7: Aggiornare `backend/services/config_service.py`** — aggiungere metodi

Aggiungere dopo `update_threshold_defaults`:

```python
def update_zone_color(self, zone_name: str, color: str) -> None:
    """Persist a zone color in config.json."""
    zone_colors = self._delta.get("zone_colors", {})
    zone_colors[zone_name] = color
    self._delta["zone_colors"] = zone_colors
    self._save_delta()

def delete_zone_color(self, zone_name: str) -> None:
    """Remove a zone color from config.json."""
    zone_colors = self._delta.get("zone_colors", {})
    zone_colors.pop(zone_name, None)
    self._delta["zone_colors"] = zone_colors
    self._save_delta()

def delete_threshold_default(self, zone_name: str) -> None:
    """Remove a zone from thresholds.defaults in config.json."""
    thresholds = self._delta.get("thresholds", {})
    defaults = thresholds.get("defaults", {})
    defaults.pop(zone_name, None)
    thresholds["defaults"] = defaults
    self._delta["thresholds"] = thresholds
    self._save_delta()

def delete_sensor_threshold(self, sensor_id: str) -> None:
    """Remove a sensor threshold override from config.json."""
    thresholds = self._delta.get("thresholds", {})
    sensors = thresholds.get("sensors", {})
    sensors.pop(sensor_id, None)
    thresholds["sensors"] = sensors
    self._delta["thresholds"] = thresholds
    self._save_delta()

def update_threshold_defaults(self, zones: dict) -> None:
    """Upsert zone defaults in thresholds.defaults.

    Args:
        zones: dict[str, ZoneThresholds] — zone name → thresholds
    """
    thresholds = self._delta.get("thresholds", {})
    defaults = thresholds.get("defaults", {})
    for zone_name, zone_thresh in zones.items():
        # Store as dict for JSON serialization
        defaults[zone_name] = (
            zone_thresh.model_dump() if hasattr(zone_thresh, "model_dump")
            else {"min": zone_thresh.min, "max": zone_thresh.max}
        )
    thresholds["defaults"] = defaults
    self._delta["thresholds"] = thresholds
    self._save_delta()
```

Nota: se `update_threshold_defaults` esiste già con firma diversa, sostituire l'intera implementazione con quella sopra.

- [ ] **Step 8: Eseguire il test — deve passare**

```bash
pytest backend/tests/test_config_service.py -v
```
Expected: tutti PASS

- [ ] **Step 9: Aggiungere metodi astratti a `backend/database/adapter.py`**

```python
@abstractmethod
async def get_size_mb(self) -> float:
    """Return approximate database size in megabytes."""

@abstractmethod
async def delete_readings_before(self, dt: datetime) -> int:
    """Delete readings older than dt. Return count of deleted rows."""

@abstractmethod
async def delete_alerts_before(self, dt: datetime) -> int:
    """Delete alerts older than dt. Return count of deleted rows."""
```

(Aggiungere `from datetime import datetime` all'header se mancante.)

- [ ] **Step 10: Implementare in `TinyFluxAdapter`**

Trovare `backend/database/tinyflux_adapter.py` e aggiungere:

```python
async def get_size_mb(self) -> float:
    import os
    try:
        return os.path.getsize(self._path) / 1_048_576
    except OSError:
        return 0.0

async def delete_readings_before(self, dt: datetime) -> int:
    # TinyFlux: leggi tutti i punti, filtra, riscrivi
    # Implementazione semplice: conta poi elimina
    from tinyflux import TimeQuery
    tq = TimeQuery()
    deleted = self._db.remove(tq < dt, measurement="readings")
    return len(deleted) if deleted else 0

async def delete_alerts_before(self, dt: datetime) -> int:
    from tinyflux import TimeQuery
    tq = TimeQuery()
    deleted = self._db.remove(tq < dt, measurement="alerts")
    return len(deleted) if deleted else 0
```

- [ ] **Step 11: Eseguire i test esistenti DB**

```bash
pytest backend/tests/ -v -k "adapter or database"
```
Expected: tutti PASS (nessuna regressione)

- [ ] **Step 12: Commit**

```bash
git add backend/models/config_model.py backend/services/config_service.py \
        backend/database/adapter.py backend/database/tinyflux_adapter.py
git commit -m "[feat] data model v2: zone_colors, archive_after_days, ThresholdDefaultsPatch generico, adapter methods"
```

---

## Task 4: Backend Health API

**Files:**
- Create: `backend/services/log_collector.py`
- Create: `backend/routers/health.py`
- Create: `backend/routers/logs.py`
- Modify: `backend/services/mqtt_client.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Creare `backend/services/log_collector.py`**

```python
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
```

- [ ] **Step 2: Aggiungere `health_state` e `discovered_sensors` a `MQTTClient`**

In `backend/services/mqtt_client.py`, nella classe `MQTTClient.__init__`:

```python
self.health_state: str = "connecting"   # "connected"|"connecting"|"disconnected"|"error"
self.discovered_sensors: set[str] = set()
self._connected_at: float | None = None
```

In `_on_connect`:
```python
self.health_state = "connected"
self._connected_at = time.time()
```

In `_on_disconnect`:
```python
self.health_state = "disconnected"
self._connected_at = None
```

In `_on_message` (dove parsifica il topic), aggiungere prima del return:
```python
self.discovered_sensors.add(sensor_id)
```

Aggiungere property:
```python
@property
def uptime_s(self) -> int:
    if self._connected_at is None:
        return 0
    return int(time.time() - self._connected_at)
```

- [ ] **Step 3: Aggiornare `backend/main.py`** — app.state, LogCollector, archive job

```python
# 1. Import aggiuntivi (top del file):
from datetime import datetime, timezone
from backend.services.log_collector import LogCollectorHandler

# 2. Rimuovere le righe 31-32 (module-level globals):
#    _mqtt_client: MQTTClient | None = None
#    _scheduler: AsyncIOScheduler | None = None

# 3. Aggiornare lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registra log collector
    log_collector = LogCollectorHandler(maxlen=1000)
    logging.getLogger().addHandler(log_collector)
    app.state.log_collector = log_collector
    app.state.started_at = datetime.now(tz=timezone.utc)

    logger.info("medMonitor backend starting — database: %s", settings.database_backend)

    get_db()
    await alert_service.restore_state()
    logger.info("AlertService state restored from DB")

    cfg = config_service.get_config()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(alert_service.check_alerts, "interval", seconds=60,
                      id="alert_check", max_instances=1)
    scheduler.add_job(imap_service.check_inbox, "interval",
                      seconds=cfg.email.imap.check_interval_seconds,
                      id="imap_check", max_instances=1)
    scheduler.add_job(_archive_job, "cron", hour=2, minute=0,
                      id="archive_check", max_instances=1)
    scheduler.start()
    app.state.scheduler = scheduler
    app.state.scheduler_started_at = datetime.now(tz=timezone.utc)
    logger.info("APScheduler started")

    loop = asyncio.get_running_loop()
    mqtt_client = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
    mqtt_client.start(loop=loop)
    app.state.mqtt_client = mqtt_client
    logger.info("MQTT client started (broker: %s:%d)", settings.mqtt_host, settings.mqtt_port)

    yield

    if app.state.mqtt_client:
        app.state.mqtt_client.stop()
    if app.state.scheduler and app.state.scheduler.running:
        app.state.scheduler.shutdown(wait=False)
    await close_db()
    logger.info("medMonitor backend shut down cleanly")


async def _archive_job():
    """Nightly archive job — called by APScheduler at 02:00."""
    from backend.services.archive_service import ArchiveService
    svc = ArchiveService(get_db(), config_service)
    await svc.run()
```

Sostituire il vecchio `health_check` con il router include (vedi Step 5).

- [ ] **Step 4: Creare `backend/routers/health.py`**

```python
"""Health + service control endpoints."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api", tags=["health"])


def _uptime_s(started_at: datetime | None) -> int:
    if started_at is None:
        return 0
    return int((datetime.now(tz=timezone.utc) - started_at).total_seconds())


@router.get("/health")
async def health(request: Request):
    from backend.dependencies import get_db
    from backend.config import settings

    mqtt = getattr(request.app.state, "mqtt_client", None)
    scheduler = getattr(request.app.state, "scheduler", None)
    started_at = getattr(request.app.state, "started_at", None)
    sched_started = getattr(request.app.state, "scheduler_started_at", None)

    try:
        db = get_db()
        db_size = await db.get_size_mb()
        db_status = "ok"
    except Exception:
        db_size = 0.0
        db_status = "error"

    return {
        "system": {
            "started_at": started_at.isoformat() if started_at else None,
            "uptime_s":   _uptime_s(started_at),
            "version":    "2.0.0",
        },
        "mqtt": {
            "status":   mqtt.health_state if mqtt else "disconnected",
            "uptime_s": mqtt.uptime_s if mqtt else 0,
            "broker":   f"{settings.mqtt_host}:{settings.mqtt_port}",
        },
        "scheduler": {
            "status":   "running" if (scheduler and scheduler.running) else "stopped",
            "uptime_s": _uptime_s(sched_started),
            "next_run": _next_run_iso(scheduler),
        },
        "db": {
            "status":   db_status,
            "uptime_s": _uptime_s(started_at),
            "backend":  settings.database_backend,
            "size_mb":  round(db_size, 2),
        },
    }


def _next_run_iso(scheduler) -> str | None:
    if scheduler is None or not scheduler.running:
        return None
    jobs = scheduler.get_jobs()
    if not jobs:
        return None
    next_times = [j.next_run_time for j in jobs if j.next_run_time]
    if not next_times:
        return None
    return min(next_times).isoformat()


@router.post("/services/mqtt/{action}")
async def control_mqtt(action: str, request: Request):
    mqtt = getattr(request.app.state, "mqtt_client", None)
    if action == "stop":
        if mqtt:
            mqtt.stop()
        return {"status": "stopped"}
    elif action == "start":
        import asyncio
        from backend.services.mqtt_client import MQTTClient
        from backend.main import _on_mqtt_reading
        loop = asyncio.get_running_loop()
        new_mqtt = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
        new_mqtt.start(loop=loop)
        request.app.state.mqtt_client = new_mqtt
        return {"status": "started"}
    elif action == "restart":
        if mqtt:
            mqtt.stop()
        import asyncio
        from backend.services.mqtt_client import MQTTClient
        from backend.main import _on_mqtt_reading
        loop = asyncio.get_running_loop()
        new_mqtt = MQTTClient(on_reading=_on_mqtt_reading, loop=loop)
        new_mqtt.start(loop=loop)
        request.app.state.mqtt_client = new_mqtt
        return {"status": "restarted"}
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/services/scheduler/{action}")
async def control_scheduler(action: str, request: Request):
    scheduler = getattr(request.app.state, "scheduler", None)
    if action == "stop":
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        return {"status": "stopped"}
    elif action == "start":
        if scheduler and not scheduler.running:
            scheduler.start()
        return {"status": "started"}
    elif action == "restart":
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        if scheduler:
            scheduler.start()
        return {"status": "restarted"}
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/services/db/restart")
async def restart_db(request: Request):
    from backend.dependencies import close_db, get_db
    await close_db()
    get_db()  # Re-initialize
    return {"status": "restarted"}
```

- [ ] **Step 5: Creare `backend/routers/logs.py`**

```python
"""Log streaming endpoint."""

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def get_logs(
    request: Request,
    level: str = Query("ALL", pattern="^(ALL|INFO|WARNING|ERROR)$"),
    limit: int = Query(200, ge=1, le=1000),
):
    collector = getattr(request.app.state, "log_collector", None)
    if collector is None:
        return []
    return collector.get_entries(level=level, limit=limit)
```

- [ ] **Step 6: Registrare i nuovi router in `backend/main.py`**

Aggiungere dopo gli altri `include_router`:

```python
from backend.routers import health as health_router
from backend.routers import logs as logs_router

# ...
app.include_router(health_router.router)
app.include_router(logs_router.router)
```

E rimuovere il vecchio `@app.get("/api/health")` (righe 126-136).

- [ ] **Step 7: Scrivere test per health endpoint**

```python
# backend/tests/test_health.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient


def test_health_returns_all_sections(test_client):
    """GET /api/health deve restituire system, mqtt, scheduler, db."""
    r = test_client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "system" in data
    assert "mqtt" in data
    assert "scheduler" in data
    assert "db" in data
    assert "version" in data["system"]
    assert "size_mb" in data["db"]
```

- [ ] **Step 8: Eseguire i test**

```bash
pytest backend/tests/test_health.py -v
```
Expected: PASS

- [ ] **Step 9: Testare manualmente**

```bash
uvicorn backend.main:app --reload --port 8000
curl http://localhost:8000/api/health | python -m json.tool
```
Expected: JSON con system/mqtt/scheduler/db senza 500 error

- [ ] **Step 10: Commit**

```bash
git add backend/services/log_collector.py backend/routers/health.py \
        backend/routers/logs.py backend/services/mqtt_client.py backend/main.py
git commit -m "[feat] backend health API v2: app.state, LogCollector, service controls, /logs"
```

---

## Task 5: Backend Zone API + Sensor Discovery

**Files:**
- Modify: `backend/routers/config.py`
- Modify: `backend/routers/sensors.py`
- Modify: `backend/routers/thresholds.py`

- [ ] **Step 1: Scrivere test per zone API**

```python
# backend/tests/test_zones.py
def test_get_zones(test_client):
    r = test_client.get("/api/zones")
    assert r.status_code == 200
    zones = r.json()
    assert isinstance(zones, list)
    # Default config ha fridge + freezer
    names = [z["name"] for z in zones]
    assert "fridge" in names
    assert "freezer" in names


def test_post_zone(test_client):
    r = test_client.post("/api/zones", json={
        "name": "cold_room",
        "color": "#a855f7",
        "threshold_min": 2.0,
        "threshold_max": 8.0,
    })
    assert r.status_code in (200, 201)
    r2 = test_client.get("/api/zones")
    names = [z["name"] for z in r2.json()]
    assert "cold_room" in names


def test_delete_zone_no_sensors(test_client):
    test_client.post("/api/zones", json={
        "name": "temp_zone", "color": "#111",
        "threshold_min": 0.0, "threshold_max": 10.0,
    })
    r = test_client.delete("/api/zones/temp_zone")
    assert r.status_code == 200
```

- [ ] **Step 2: Eseguire i test — devono fallire**

```bash
pytest backend/tests/test_zones.py -v
```
Expected: FAIL (endpoint non esistono)

- [ ] **Step 3: Aggiornare `backend/routers/config.py`** — aggiungere zone endpoints

```python
from pydantic import BaseModel

class ZoneCreate(BaseModel):
    name: str
    color: str
    threshold_min: float
    threshold_max: float


@router.get("/api/zones")
async def list_zones():
    """List all zones with thresholds and colors."""
    cfg = config_service.get_config()
    result = []
    for zone_name, zone_thresh in cfg.thresholds.defaults.items():
        result.append({
            "name": zone_name,
            "color": cfg.zone_colors.get(zone_name, "#64748b"),
            "threshold_min": zone_thresh.min,
            "threshold_max": zone_thresh.max,
        })
    return result


@router.post("/api/zones")
async def create_or_update_zone(body: ZoneCreate):
    """Upsert a zone with thresholds and color (create or update if already exists)."""
    from backend.models.config_model import ZoneThresholds
    try:
        config_service.update_threshold_defaults(
            {body.name: ZoneThresholds(min=body.threshold_min, max=body.threshold_max)}
        )
        config_service.update_zone_color(body.name, body.color)
        return {"name": body.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/zones/{zone_name}")
async def delete_zone(zone_name: str):
    """Delete a zone. Returns 409 if sensors are assigned."""
    from backend.paths import data_file
    import json
    sensors_file = data_file("sensors.json")
    if sensors_file.exists():
        sensors = json.loads(sensors_file.read_text(encoding="utf-8"))
        if any(s.get("zone") == zone_name for s in sensors.values()):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail=f"Zone '{zone_name}' ha sensori assegnati. Riassegna prima i sensori."
            )
    config_service.delete_threshold_default(zone_name)
    config_service.delete_zone_color(zone_name)
    return {"deleted": zone_name}
```

Nota: `update_threshold_defaults` e `delete_threshold_default` devono gestire zone arbitrarie — verificare `config_service.py` e aggiornare se necessario.

- [ ] **Step 4: Aggiornare `backend/routers/thresholds.py`** per ThresholdDefaultsPatch.zones

Trovare la sezione che usa `patch.fridge`/`patch.freezer` e sostituire con:

```python
@router.patch("/api/thresholds/defaults")
async def patch_threshold_defaults(patch: ThresholdDefaultsPatch):
    if patch.zones:
        config_service.update_threshold_defaults(patch.zones)
    return config_service.get_config().thresholds.defaults
```

Aggiornare anche `ConfigService.update_threshold_defaults` per accettare `dict[str, ZoneThresholds]`.

- [ ] **Step 5: Aggiornare `backend/routers/sensors.py`** — /discovered, /accept, DELETE

Aggiungere PRIMA del route `/{sensor_id}` esistente:

```python
@router.get("/api/sensors/discovered")
async def get_discovered(request: Request):
    """List sensors detected via MQTT not yet in sensors.json."""
    from backend.paths import data_file
    import json
    mqtt = getattr(request.app.state, "mqtt_client", None)
    discovered = mqtt.discovered_sensors if mqtt else set()

    sensors_file = data_file("sensors.json")
    configured = set()
    if sensors_file.exists():
        configured = set(json.loads(sensors_file.read_text(encoding="utf-8")).keys())

    # Solo quelli non ancora configurati
    new_ids = discovered - configured
    return [{"sensor_id": sid, "first_seen": None, "last_seen": None, "last_temp": None}
            for sid in sorted(new_ids)]


class SensorAcceptBody(BaseModel):
    name: str
    zone: str
    min: float | None = None
    max: float | None = None

@router.post("/api/sensors/{sensor_id}/accept")
async def accept_sensor(sensor_id: str, body: SensorAcceptBody):
    """Accept a discovered sensor: register it and optionally set thresholds."""
    from backend.paths import data_file
    import json
    sensors_file = data_file("sensors.json")
    sensors = {}
    if sensors_file.exists():
        sensors = json.loads(sensors_file.read_text(encoding="utf-8"))
    sensors[sensor_id] = {"name": body.name, "zone": body.zone, "active": True}
    sensors_file.write_text(json.dumps(sensors, indent=2), encoding="utf-8")

    if body.min is not None and body.max is not None:
        from backend.models.config_model import SensorThreshold
        cfg = config_service.get_config()
        existing = cfg.thresholds.sensors.get(sensor_id, SensorThreshold())
        existing.name = body.name
        existing.zone = body.zone
        existing.min = body.min
        existing.max = body.max
        existing.override = True
        config_service.update_sensor_threshold(sensor_id, existing)

    return {"accepted": sensor_id}


@router.delete("/api/sensors/{sensor_id}")
async def delete_sensor(sensor_id: str):
    """Remove sensor from sensors.json and thresholds (data preserved in DB)."""
    from backend.paths import data_file
    import json
    sensors_file = data_file("sensors.json")
    if sensors_file.exists():
        sensors = json.loads(sensors_file.read_text(encoding="utf-8"))
        sensors.pop(sensor_id, None)
        sensors_file.write_text(json.dumps(sensors, indent=2), encoding="utf-8")
    config_service.delete_sensor_threshold(sensor_id)
    return {"deleted": sensor_id}
```

Nota: verificare che `config_service.delete_sensor_threshold` esista; se no, aggiungerlo seguendo il pattern delta-save.

- [ ] **Step 6: Eseguire i test**

```bash
pytest backend/tests/test_zones.py backend/tests/ -v
```
Expected: test_zones PASS, nessuna regressione

- [ ] **Step 7: Commit**

```bash
git add backend/routers/config.py backend/routers/sensors.py backend/routers/thresholds.py \
        backend/services/config_service.py backend/main.py
git commit -m "[feat] zone API + sensor discovery: GET/POST/DELETE /api/zones, /discovered, /accept, DELETE sensor"
```

---

## Task 6: Dashboard Redesign

**Files:**
- Modify: `frontend/components/zone_card.py`
- Create: `frontend/components/sensors_table.py`
- Modify: `frontend/pages/dashboard.py`
- Modify: `frontend/callbacks/dashboard_callbacks.py`

- [ ] **Step 1: Riscrivere `frontend/components/zone_card.py`**

```python
"""Zone card v2 — Modern SaaS Light design."""

from dash import html


def zone_card(zone_name: str, zone_color: str, status: str,
              temp: float | None, sensors: list[dict],
              threshold_min: float, threshold_max: float) -> html.Div:
    """
    Args:
        sensors: lista di {name, temp, battery_pct}
    """
    status_class = {"OK": "mm-badge-ok", "WARNING": "mm-badge-warn", "CRITICAL": "mm-badge-critical"}.get(status, "mm-badge-info")
    card_class = {"OK": "mm-card-ok", "WARNING": "mm-card-warn", "CRITICAL": "mm-card-critical"}.get(status, "mm-card")
    temp_class = {"OK": "mm-temp-ok", "WARNING": "mm-temp-warn", "CRITICAL": "mm-temp-critical"}.get(status, "")

    temp_str = f"{temp:.1f}°C" if temp is not None else "–"

    # Progress bar position
    if temp is not None and threshold_max > threshold_min:
        pct = max(0, min(100, (temp - threshold_min) / (threshold_max - threshold_min) * 100))
    else:
        pct = 0

    sensor_rows = []
    for s in sensors:
        bat = s.get("battery_pct")
        bat_str = f"🔋 {bat}%" if bat is not None else ""
        sensor_rows.append(
            html.Div(
                [
                    html.Span(s.get("name", s.get("id", "?")), style={"fontSize": "11px", "color": "#374151"}),
                    html.Span(
                        f"{s['temp']:.1f}°C" if s.get("temp") is not None else "–",
                        style={"fontSize": "11px", "color": "#64748b", "marginLeft": "6px"},
                    ),
                    html.Span(bat_str, style={"fontSize": "10px", "color": "#94a3b8", "marginLeft": "6px"}),
                ],
                style={"display": "flex", "alignItems": "center", "padding": "2px 0"},
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(zone_name.upper(), style={"fontSize": "11px", "fontWeight": "600", "color": "#64748b"}),
                    html.Span(status, className=status_class),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
            ),
            html.Div(temp_str, style={"fontSize": "36px", "fontWeight": "800", "lineHeight": "1"}, className=temp_class),
            html.Div(sensor_rows, style={"margin": "8px 0"}),
            # Progress bar
            html.Div(
                html.Div(
                    style={"width": f"{pct}%", "height": "100%", "background": zone_color, "borderRadius": "2px", "transition": "width 0.5s"},
                ),
                style={"height": "4px", "background": "#f1f5f9", "borderRadius": "2px", "marginTop": "8px"},
            ),
            html.Div(
                [
                    html.Span(f"{threshold_min}°C", style={"fontSize": "10px", "color": "#94a3b8"}),
                    html.Span(f"{threshold_max}°C", style={"fontSize": "10px", "color": "#94a3b8"}),
                ],
                style={"display": "flex", "justifyContent": "space-between", "marginTop": "3px"},
            ),
        ],
        className=f"mm-card {card_class}",
        style={"borderLeft": f"4px solid {zone_color}"},
    )
```

- [ ] **Step 2: Creare `frontend/components/sensors_table.py`**

```python
"""Compact sensors table for Dashboard."""

from dash import html


def sensors_table(sensors: list[dict]) -> html.Div:
    """
    Args:
        sensors: lista di {id, name, zone, zone_color, temp, battery_pct, last_seen_s}
    """
    if not sensors:
        return html.Div("Nessun sensore rilevato.", style={"color": "#94a3b8", "fontSize": "13px", "padding": "16px"})

    rows = []
    for s in sensors:
        bat = s.get("battery_pct")
        bat_pct = bat if bat is not None else 0
        bat_color = "#22c55e" if bat_pct > 50 else "#f59e0b" if bat_pct > 20 else "#ef4444"

        last = s.get("last_seen_s")
        last_str = f"{last}s fa" if last is not None else "–"
        color = s.get("zone_color", "#64748b")

        rows.append(
            html.Tr([
                html.Td(s.get("id", "?"), style={"fontSize": "11px", "color": "#94a3b8", "fontFamily": "monospace"}),
                html.Td(s.get("name") or s.get("id", "?"), style={"fontSize": "12px"}),
                html.Td(
                    html.Span(
                        s.get("zone", "–"),
                        style={"background": color + "22", "color": color, "borderRadius": "4px",
                               "padding": "1px 6px", "fontSize": "11px", "fontWeight": "600"},
                    )
                ),
                html.Td(
                    f"{s['temp']:.1f}°C" if s.get("temp") is not None else "–",
                    style={"fontSize": "13px", "fontWeight": "600"},
                ),
                html.Td(
                    html.Div(
                        html.Div(style={"width": f"{bat_pct}%", "height": "100%",
                                        "background": bat_color, "borderRadius": "2px"}),
                        title=f"{bat_pct}%",
                        style={"width": "40px", "height": "6px", "background": "#f1f5f9", "borderRadius": "2px"},
                    )
                ),
                html.Td(last_str, style={"fontSize": "11px", "color": "#94a3b8"}),
            ])
        )

    return html.Div(
        html.Table(
            [
                html.Thead(html.Tr([
                    html.Th("ID", style={"fontSize": "10px", "color": "#94a3b8", "fontWeight": "600", "padding": "4px 8px"}),
                    html.Th("Nome"),
                    html.Th("Zona"),
                    html.Th("Temp"),
                    html.Th("Batteria"),
                    html.Th("Ultimo"),
                ])),
                html.Tbody(rows),
            ],
            style={"width": "100%", "borderCollapse": "collapse", "fontSize": "12px"},
        ),
        className="mm-card",
        style={"overflowX": "auto"},
    )
```

- [ ] **Step 3: Riscrivere `frontend/pages/dashboard.py`**

```python
"""Dashboard page layout v2."""

from dash import html, dcc


def layout():
    return html.Div(
        [
            # Page header
            html.Div(
                [
                    html.H1("Dashboard", className="mm-page-title"),
                    html.Div(
                        [
                            html.Span("–", id="dashboard-updated-ts",
                                      style={"fontSize": "12px", "color": "#94a3b8", "marginRight": "8px"}),
                            html.Button("↻ Aggiorna", id="dashboard-refresh-btn",
                                        style={"background": "none", "border": "1px solid #e2e8f0",
                                               "borderRadius": "6px", "padding": "4px 10px",
                                               "fontSize": "12px", "cursor": "pointer", "color": "#64748b"}),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                ],
                className="mm-page-header",
            ),
            # Error banner (hidden by default)
            html.Div(id="dashboard-error-banner", style={"display": "none"}),
            # Zone cards grid
            html.Div(id="dashboard-zone-cards",
                     style={"display": "grid",
                            "gridTemplateColumns": "repeat(auto-fill, minmax(280px, 1fr))",
                            "gap": "16px", "marginBottom": "20px"}),
            # 24h chart
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Temperatura — ultime 24h", style={"fontSize": "14px", "fontWeight": "700"}),
                            html.Div(
                                [
                                    html.Button("6h",  id="chart-range-6h",  n_clicks=0,
                                                style={"background": "#f1f5f9", "border": "none", "borderRadius": "6px",
                                                       "padding": "4px 10px", "fontSize": "11px", "color": "#64748b", "cursor": "pointer"}),
                                    html.Button("24h", id="chart-range-24h", n_clicks=0,
                                                style={"background": "#0f172a", "border": "none", "borderRadius": "6px",
                                                       "padding": "4px 10px", "fontSize": "11px", "color": "#fff", "cursor": "pointer"}),
                                    html.Button("7g",  id="chart-range-7d",  n_clicks=0,
                                                style={"background": "#f1f5f9", "border": "none", "borderRadius": "6px",
                                                       "padding": "4px 10px", "fontSize": "11px", "color": "#64748b", "cursor": "pointer"}),
                                ],
                                style={"display": "flex", "gap": "4px"},
                            ),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                               "marginBottom": "12px"},
                    ),
                    dcc.Graph(id="dashboard-chart", config={"displayModeBar": False},
                              style={"height": "300px"}),
                ],
                className="mm-card",
                style={"marginBottom": "20px"},
            ),
            # Sensors table
            html.Div(
                [
                    html.Div("Sensori", style={"fontSize": "14px", "fontWeight": "700", "marginBottom": "12px"}),
                    html.Div(id="dashboard-sensors-table"),
                ],
                className="mm-card",
            ),
        ]
    )
```

- [ ] **Step 4: Aggiornare `frontend/callbacks/dashboard_callbacks.py`** — resilienza + zone dinamiche

```python
"""Dashboard callbacks v2 — zone dinamiche, resilienza API."""

import requests
from datetime import datetime
from dash import Input, Output, callback, html
from frontend.components.zone_card import zone_card
from frontend.components.sensors_table import sensors_table

API = "http://localhost:8000"


def _safe_get(path: str):
    try:
        r = requests.get(f"{API}{path}", timeout=3)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


@callback(
    Output("dashboard-zone-cards", "children"),
    Output("dashboard-sensors-table", "children"),
    Output("dashboard-updated-ts", "children"),
    Output("dashboard-error-banner", "children"),
    Output("dashboard-error-banner", "style"),
    Input("interval-30s", "n_intervals"),
    Input("dashboard-refresh-btn", "n_clicks"),
)
def update_dashboard(n, _clicks):
    zones, err1 = _safe_get("/api/zones")
    readings, err2 = _safe_get("/api/readings/latest")
    sensors_cfg, err3 = _safe_get("/api/sensors")

    if err1 or err2:
        error_msg = html.Div(
            f"⚠ Backend non raggiungibile: {err1 or err2}",
            style={"background": "#fef3c7", "border": "1px solid #f59e0b",
                   "borderRadius": "8px", "padding": "10px 16px",
                   "fontSize": "13px", "color": "#92400e", "marginBottom": "16px"},
        )
        return [], html.Div("–"), "–", error_msg, {"display": "block"}

    # Build zone cards
    readings_map = {r["sensor_id"]: r for r in (readings or [])}
    sensor_map = {s["id"]: s for s in (sensors_cfg or [])}

    zone_cards = []
    all_sensor_rows = []

    for zone in (zones or []):
        zone_name = zone["name"]
        zone_color = zone.get("color", "#64748b")
        t_min = zone.get("threshold_min", 0)
        t_max = zone.get("threshold_max", 30)

        zone_sensors = [s for s in sensor_map.values() if s.get("zone") == zone_name]
        sensor_data = []
        temps = []
        for s in zone_sensors:
            r = readings_map.get(s["id"], {})
            t = r.get("temperature")
            if t is not None:
                temps.append(t)
            sensor_data.append({
                "id": s["id"], "name": s.get("name", s["id"]),
                "temp": t, "battery_pct": r.get("battery"),
            })
            all_sensor_rows.append({
                "id": s["id"], "name": s.get("name", s["id"]),
                "zone": zone_name, "zone_color": zone_color,
                "temp": t, "battery_pct": r.get("battery"),
                "last_seen_s": r.get("age_seconds"),
            })

        avg_temp = sum(temps) / len(temps) if temps else None
        if avg_temp is None:
            status = "OK"
        elif t_min <= avg_temp <= t_max:
            status = "OK"
        elif avg_temp < t_min - 5 or avg_temp > t_max + 5:
            status = "CRITICAL"
        else:
            status = "WARNING"

        zone_cards.append(zone_card(zone_name, zone_color, status, avg_temp,
                                    sensor_data, t_min, t_max))

    ts = datetime.now().strftime("Aggiornato alle %H:%M:%S")
    return zone_cards, sensors_table(all_sensor_rows), ts, "", {"display": "none"}
```

- [ ] **Step 5: Aggiornare sidebar alert badge da dashboard callback**

Aggiungere callback per `sidebar-alert-badge`. Usa `GET /api/alerts` (endpoint esistente) e conta gli allarmi con `acknowledged=false`:

```python
@callback(
    Output("sidebar-alert-badge", "children"),
    Output("sidebar-alert-badge", "style"),
    Input("interval-60s", "n_intervals"),
)
def update_alert_badge(n):
    base_style = {"background": "#ef4444", "color": "#fff", "borderRadius": "10px",
                  "padding": "0 6px", "fontSize": "10px", "fontWeight": "700"}
    data, err = _safe_get("/api/alerts?acknowledged=false&limit=100")
    if err or data is None:
        return "0", {**base_style, "display": "none"}
    # data may be a list or a dict with "alerts" key — handle both
    items = data if isinstance(data, list) else data.get("alerts", [])
    count = len(items)
    if count == 0:
        return "0", {**base_style, "display": "none"}
    return str(count), {**base_style, "display": "inline"}
```

Nota: verificare il response format di `GET /api/alerts` in `backend/routers/alerts.py` e adattare il parsing di `items` se necessario.

- [ ] **Step 6: Verificare dashboard**

```bash
python frontend/app.py
```
Aprire http://localhost:8050/ — verificare zone cards, tabella sensori, nessun crash se backend non risponde.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/zone_card.py frontend/components/sensors_table.py \
        frontend/pages/dashboard.py frontend/callbacks/dashboard_callbacks.py
git commit -m "[feat] dashboard v2: zone cards dinamiche, sensors table, resilienza API"
```

---

## Task 7: Pagina Sistema

**Files:**
- Create: `frontend/components/service_status.py`
- Create: `frontend/components/log_panel.py`
- Modify: `frontend/pages/system.py`
- Modify: `frontend/callbacks/system_callbacks.py`

- [ ] **Step 1: Creare `frontend/components/service_status.py`**

```python
"""Service status card component."""

from dash import html


def service_card(
    service_id: str,
    display_name: str,
    status: str,
    uptime_str: str,
    details: str = "",
    supports_stop: bool = True,
) -> html.Div:
    dot_class = {
        "connected": "mm-dot-ok", "running": "mm-dot-ok", "ok": "mm-dot-ok",
        "stopping": "mm-dot-warn", "degraded": "mm-dot-warn",
        "disconnected": "mm-dot-error", "stopped": "mm-dot-error", "error": "mm-dot-error",
    }.get(status, "mm-dot-warn")

    # disabled=False must be set explicitly so pattern-matching Output("disabled") works in Dash
    buttons = [
        html.Button(
            "Restart",
            id={"type": "service-btn", "service": service_id, "action": "restart"},
            n_clicks=0,
            disabled=False,
            style={"background": "#f1f5f9", "border": "1px solid #e2e8f0", "borderRadius": "6px",
                   "padding": "3px 10px", "fontSize": "11px", "cursor": "pointer", "marginLeft": "4px"},
        )
    ]
    if supports_stop:
        buttons.insert(0, html.Button(
            "Stop",
            id={"type": "service-btn", "service": service_id, "action": "stop"},
            n_clicks=0,
            disabled=False,
            style={"background": "#fee2e2", "color": "#991b1b", "border": "none", "borderRadius": "6px",
                   "padding": "3px 10px", "fontSize": "11px", "cursor": "pointer"},
        ))

    return html.Div(
        [
            html.Div(
                [
                    html.Div([
                        html.Span("", className=f"mm-status-dot {dot_class}", style={"marginRight": "8px"}),
                        html.Span(display_name, style={"fontWeight": "600", "fontSize": "13px"}),
                    ], style={"display": "flex", "alignItems": "center"}),
                    html.Div(buttons, style={"display": "flex"}),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
            ),
            html.Div(uptime_str, style={"fontSize": "11px", "color": "#94a3b8", "marginTop": "4px"}),
            html.Div(details, style={"fontSize": "10px", "color": "#64748b", "marginTop": "2px"}) if details else None,
        ],
        className="mm-card",
        style={"marginBottom": "12px"},
    )
```

- [ ] **Step 2: Creare `frontend/components/log_panel.py`**

```python
"""Log panel component — terminal dark style."""

from dash import html, dcc


def log_panel() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Log di sistema", style={"fontWeight": "700", "fontSize": "13px"}),
                    html.Div(
                        [
                            html.Button("ALL",     id="log-filter-ALL",     n_clicks=1,
                                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer"}),
                            html.Button("INFO",    id="log-filter-INFO",    n_clicks=0,
                                        style={"background": "#f1f5f9", "color": "#64748b", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer", "marginLeft": "2px"}),
                            html.Button("WARNING", id="log-filter-WARNING", n_clicks=0,
                                        style={"background": "#f1f5f9", "color": "#64748b", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer", "marginLeft": "2px"}),
                            html.Button("ERROR",   id="log-filter-ERROR",   n_clicks=0,
                                        style={"background": "#f1f5f9", "color": "#64748b", "border": "none",
                                               "borderRadius": "4px", "padding": "2px 8px", "fontSize": "10px", "cursor": "pointer", "marginLeft": "2px"}),
                        ],
                        style={"display": "flex"},
                    ),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                       "marginBottom": "8px"},
            ),
            html.Div(id="log-panel-content", className="mm-log-panel"),
            dcc.Store(id="log-filter-store", data="ALL"),
        ],
        className="mm-card",
    )
```

- [ ] **Step 3: Riscrivere `frontend/pages/system.py`**

```python
"""Pagina Sistema — monitoraggio e controllo servizi backend."""

from dash import html
from frontend.components.service_status import service_card
from frontend.components.log_panel import log_panel


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Sistema", className="mm-page-title"),
                    html.Div(
                        html.Span("–", id="system-updated-ts",
                                  style={"fontSize": "12px", "color": "#94a3b8"}),
                    ),
                ],
                className="mm-page-header",
            ),
            html.Div(
                [
                    # Colonna 1 — Servizi
                    html.Div(
                        [
                            html.Div("Servizi", style={"fontWeight": "700", "fontSize": "13px",
                                                        "marginBottom": "12px", "color": "#64748b",
                                                        "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                            html.Div(id="service-cards-container"),
                        ],
                        style={"flex": "1", "minWidth": "220px"},
                    ),
                    # Colonna 2 — Log
                    html.Div(
                        log_panel(),
                        style={"flex": "2", "minWidth": "320px"},
                    ),
                    # Colonna 3 — Metriche
                    html.Div(
                        [
                            html.Div("Metriche", style={"fontWeight": "700", "fontSize": "13px",
                                                          "marginBottom": "12px", "color": "#64748b",
                                                          "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                            html.Div(id="system-metrics-container"),
                            html.Button(
                                "📦 Archivia ora",
                                id="archive-now-btn",
                                n_clicks=0,
                                style={"marginTop": "16px", "background": "#0f172a", "color": "#fff",
                                       "border": "none", "borderRadius": "8px", "padding": "8px 16px",
                                       "fontSize": "13px", "cursor": "pointer", "width": "100%"},
                            ),
                            html.Div(id="archive-result", style={"marginTop": "8px", "fontSize": "12px"}),
                        ],
                        style={"flex": "1", "minWidth": "200px"},
                    ),
                ],
                style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
            ),
        ]
    )
```

- [ ] **Step 4: Implementare `frontend/callbacks/system_callbacks.py`**

```python
"""Sistema page callbacks — health, logs, service controls, archive."""

import requests
from datetime import datetime
from dash import Input, Output, State, callback, html, ALL, ctx
from frontend.components.service_status import service_card

API = "http://localhost:8000"


def _safe_get(path: str):
    try:
        r = requests.get(f"{API}{path}", timeout=3)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def _safe_post(path: str):
    try:
        r = requests.post(f"{API}{path}", timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def _uptime_str(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"attivo da {h}h {m}m" if h > 0 else f"attivo da {m}m"


@callback(
    Output("service-cards-container", "children"),
    Output("system-metrics-container", "children"),
    Output("system-updated-ts", "children"),
    Output("dot-mqtt", "className"),
    Output("dot-scheduler", "className"),
    Output("dot-db", "className"),
    Input("interval-30s", "n_intervals"),
)
def update_system_status(n):
    health, err = _safe_get("/api/health")
    ts = datetime.now().strftime("Aggiornato alle %H:%M:%S")

    if err or health is None:
        error_card = html.Div("⚠ Backend non raggiungibile",
                              style={"background": "#fef3c7", "border": "1px solid #f59e0b",
                                     "borderRadius": "8px", "padding": "12px", "fontSize": "13px"})
        return error_card, html.Div("–"), ts, "mm-status-dot mm-dot-error", "mm-status-dot mm-dot-error", "mm-status-dot mm-dot-error"

    mqtt = health.get("mqtt", {})
    sched = health.get("scheduler", {})
    db = health.get("db", {})
    sys_info = health.get("system", {})

    mqtt_status = mqtt.get("status", "disconnected")
    sched_status = sched.get("status", "stopped")
    db_status = db.get("status", "error")

    dot_cls = lambda s: "mm-status-dot mm-dot-ok" if s in ("connected", "running", "ok") else \
                         "mm-status-dot mm-dot-warn" if s in ("degraded",) else "mm-status-dot mm-dot-error"

    cards = [
        service_card("mqtt", "MQTT", mqtt_status,
                     _uptime_str(mqtt.get("uptime_s", 0)),
                     details=mqtt.get("broker", ""),
                     supports_stop=True),
        service_card("scheduler", "APScheduler", sched_status,
                     _uptime_str(sched.get("uptime_s", 0)),
                     details=f"next: {sched.get('next_run', '–')}",
                     supports_stop=True),
        service_card("db", "Database", db_status,
                     _uptime_str(db.get("uptime_s", 0)),
                     details=f"{db.get('backend', '?')} · {db.get('size_mb', 0):.1f} MB",
                     supports_stop=False),
    ]

    # Archive status
    arc, _ = _safe_get("/api/archive/status")
    last_arc = "mai" if not arc or not arc.get("last_run") else arc["last_run"][:10]
    last_rows = arc.get("last_rows_archived", 0) if arc else 0

    metrics = html.Div(
        [
            _metric("Uptime sistema", _uptime_str(sys_info.get("uptime_s", 0))),
            _metric("Versione", sys_info.get("version", "?")),
            _metric("Dimensione DB", f"{db.get('size_mb', 0):.1f} MB"),
            _metric("Ultima archiviazione", f"{last_arc} ({last_rows} righe)"),
        ],
        className="mm-card",
    )

    return cards, metrics, ts, dot_cls(mqtt_status), dot_cls(sched_status), dot_cls(db_status)


def _metric(label: str, value: str) -> html.Div:
    return html.Div(
        [
            html.Div(label, style={"fontSize": "11px", "color": "#94a3b8", "textTransform": "uppercase",
                                    "letterSpacing": "0.5px", "fontWeight": "600"}),
            html.Div(value, style={"fontSize": "14px", "fontWeight": "700", "color": "#0f172a", "marginBottom": "10px"}),
        ]
    )


@callback(
    Output("log-panel-content", "children"),
    Output("log-filter-store", "data"),
    Input("interval-5s", "n_intervals"),
    Input("log-filter-ALL", "n_clicks"),
    Input("log-filter-INFO", "n_clicks"),
    Input("log-filter-WARNING", "n_clicks"),
    Input("log-filter-ERROR", "n_clicks"),
    State("log-filter-store", "data"),
)
def update_logs(n, _all, _info, _warn, _err, current_filter):
    triggered = ctx.triggered_id
    level = current_filter
    if triggered in ("log-filter-ALL", "log-filter-INFO", "log-filter-WARNING", "log-filter-ERROR"):
        level = triggered.replace("log-filter-", "")

    entries, err = _safe_get(f"/api/logs?level={level}&limit=200")
    if err or entries is None:
        return html.Div("–"), level

    lines = []
    for e in reversed(entries):
        lvl = e.get("level", "INFO")
        cls = {"WARNING": "mm-log-warning", "ERROR": "mm-log-error"}.get(lvl, "mm-log-info")
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        lines.append(html.Div(
            f"[{ts}] {lvl:8s} {e.get('service', '')} — {e.get('message', '')}",
            className=cls,
            style={"marginBottom": "1px", "whiteSpace": "pre-wrap", "wordBreak": "break-all"},
        ))
    return lines, level


@callback(
    Output("archive-result", "children"),
    Input("archive-now-btn", "n_clicks"),
    prevent_initial_call=True,
)
def run_archive(n_clicks):
    result, err = _safe_post("/api/archive/run")
    if err:
        return html.Span(f"Errore: {err}", style={"color": "#ef4444"})
    rows = result.get("rows_archived", 0)
    return html.Span(f"✓ {rows} righe archiviate", style={"color": "#22c55e"})
```

- [ ] **Step 5: Verificare pagina Sistema**

Aprire http://localhost:8050/sistema — verificare layout 3 colonne, log panel, metriche.
Se backend non risponde: messaggio errore senza crash.

- [ ] **Step 5b: Aggiungere callback service control buttons**

In `system_callbacks.py`, aggiungere il callback per i pulsanti stop/restart di ogni servizio. I bottoni usano pattern-matching IDs `{"type": "service-btn", "service": service_id, "action": "restart|stop|start"}`:

```python
from dash import MATCH

@callback(
    Output({"type": "service-btn", "service": MATCH, "action": MATCH}, "disabled"),
    Input({"type": "service-btn", "service": MATCH, "action": MATCH}, "n_clicks"),
    State({"type": "service-btn", "service": MATCH, "action": MATCH}, "id"),
    prevent_initial_call=True,
)
def handle_service_action(n_clicks, btn_id):
    service = btn_id["service"]
    action  = btn_id["action"]
    _safe_post(f"/api/services/{service}/{action}")
    return False  # re-enable button after action
```

Nota: il callback usa `MATCH` — importare da `dash`. Il return `False` re-abilita il bottone subito; il vero stato aggiornato arriva al prossimo `interval-30s` poll.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/service_status.py frontend/components/log_panel.py \
        frontend/pages/system.py frontend/callbacks/system_callbacks.py
git commit -m "[feat] pagina Sistema: servizi, log panel, metriche, archivia ora, service controls"
```

---

## Task 8: Impostazioni v2

**Files:**
- Modify: `frontend/pages/settings.py`
- Modify: `frontend/callbacks/settings_callbacks.py`

- [ ] **Step 1: Riscrivere `frontend/pages/settings.py`** — 5 tab

```python
"""Impostazioni v2 — 5 tab: Sensori, Soglie, Email/Alert, Generale, Demo."""

import dash_bootstrap_components as dbc
from dash import html, dcc


def layout():
    return html.Div(
        [
            html.Div(
                html.H1("Impostazioni", className="mm-page-title"),
                className="mm-page-header",
            ),
            dbc.Tabs(
                [
                    dbc.Tab(_tab_sensors(), label="Sensori", tab_id="tab-sensors"),
                    dbc.Tab(_tab_thresholds(), label="Soglie", tab_id="tab-thresholds"),
                    dbc.Tab(_tab_email(), label="Email / Alert", tab_id="tab-email"),
                    dbc.Tab(_tab_general(), label="Generale", tab_id="tab-general"),
                    dbc.Tab(_tab_demo(), label="Demo", tab_id="tab-demo"),
                ],
                id="settings-tabs",
                active_tab="tab-sensors",
            ),
            dcc.Store(id="settings-save-trigger"),
        ]
    )


def _tab_sensors():
    return html.Div(
        [
            # Discovered sensors
            html.Div(
                [
                    html.Div("Rilevati automaticamente",
                             style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "8px"}),
                    html.Div(id="discovered-sensors-list"),
                    html.Div(id="accept-sensor-modal-container"),
                ],
                className="mm-card",
                style={"marginBottom": "16px", "marginTop": "16px"},
            ),
            # Configured sensors
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Sensori configurati",
                                     style={"fontSize": "13px", "fontWeight": "700"}),
                            html.Button("+ Aggiungi manualmente", id="add-sensor-manual-btn",
                                        n_clicks=0,
                                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                                               "borderRadius": "6px", "padding": "6px 12px", "fontSize": "12px",
                                               "cursor": "pointer"}),
                        ],
                        style={"display": "flex", "justifyContent": "space-between",
                               "alignItems": "center", "marginBottom": "12px"},
                    ),
                    html.Div(id="configured-sensors-grid"),
                ],
                className="mm-card",
            ),
        ]
    )


def _tab_thresholds():
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Zone e soglie",
                             style={"fontSize": "13px", "fontWeight": "700"}),
                    html.Button("+ Aggiungi zona", id="add-zone-btn", n_clicks=0,
                                style={"background": "#0f172a", "color": "#fff", "border": "none",
                                       "borderRadius": "6px", "padding": "6px 12px", "fontSize": "12px",
                                       "cursor": "pointer"}),
                ],
                style={"display": "flex", "justifyContent": "space-between",
                       "alignItems": "center", "marginBottom": "16px", "marginTop": "16px"},
            ),
            # Zone list con RangeSlider per ogni zona (popolato da callback)
            html.Div(id="zones-threshold-list"),
            html.Div(id="zone-modal-container"),
        ]
    )


def _tab_email():
    return html.Div(
        [
            html.Div("Email / Alert",
                     style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "16px", "marginTop": "16px"}),
            html.Div(id="email-settings-form"),
            html.Button("Salva", id="save-email-btn", n_clicks=0,
                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                               "borderRadius": "6px", "padding": "8px 16px", "fontSize": "13px", "cursor": "pointer"}),
            html.Div(id="email-save-result", style={"marginTop": "8px", "fontSize": "12px"}),
        ]
    )


def _tab_general():
    return html.Div(
        [
            html.Div("Impostazioni generali",
                     style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "16px", "marginTop": "16px"}),
            html.Div(
                [
                    html.Label("Nome impianto", style={"fontSize": "12px", "fontWeight": "600"}),
                    dcc.Input(id="setting-app-name", type="text", debounce=True,
                              style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                     "borderRadius": "6px", "fontSize": "13px", "marginBottom": "12px"}),
                    html.Label("Intervallo polling (minuti)", style={"fontSize": "12px", "fontWeight": "600"}),
                    dcc.Input(id="setting-polling-interval", type="number", min=1, max=60, debounce=True,
                              style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                     "borderRadius": "6px", "fontSize": "13px", "marginBottom": "12px"}),
                    html.Label("Archiviazione dati dopo (giorni)", style={"fontSize": "12px", "fontWeight": "600"}),
                    dcc.Input(id="setting-archive-days", type="number", min=30, max=3650, debounce=True,
                              style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                     "borderRadius": "6px", "fontSize": "13px", "marginBottom": "12px"}),
                    html.Div(
                        "Dopo questo numero di giorni, i dati vengono esportati in CSV e rimossi dal database.",
                        style={"fontSize": "11px", "color": "#94a3b8", "marginBottom": "16px"},
                    ),
                ],
                className="mm-card",
                style={"maxWidth": "480px", "marginBottom": "16px"},
            ),
            html.Button("Salva", id="save-general-btn", n_clicks=0,
                        style={"background": "#0f172a", "color": "#fff", "border": "none",
                               "borderRadius": "6px", "padding": "8px 16px", "fontSize": "13px", "cursor": "pointer"}),
            html.Div(id="general-save-result", style={"marginTop": "8px", "fontSize": "12px"}),
        ]
    )


def _tab_demo():
    return html.Div(
        [
            html.Div("Modalità demo",
                     style={"fontSize": "13px", "fontWeight": "700", "marginBottom": "16px", "marginTop": "16px"}),
            html.Div(id="demo-settings-content"),
        ]
    )
```

- [ ] **Step 2: Aggiornare `frontend/callbacks/settings_callbacks.py`** — sensor discovery + zone

Aggiungere callback per discovered sensors e zone management (mantenere callback esistenti):

```python
import requests
from dash import Input, Output, State, callback, html, ALL, ctx, no_update
import dash_bootstrap_components as dbc

API = "http://localhost:8000"


def _safe_get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=3)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def _safe_post(path, json=None):
    try:
        r = requests.post(f"{API}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def _safe_delete(path):
    try:
        r = requests.delete(f"{API}{path}", timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


@callback(
    Output("discovered-sensors-list", "children"),
    Input("interval-60s", "n_intervals"),
    Input("settings-tabs", "active_tab"),
)
def update_discovered(n, active_tab):
    if active_tab != "tab-sensors":
        return no_update
    sensors, err = _safe_get("/api/sensors/discovered")
    if err or not sensors:
        return html.Div("Nessun sensore nuovo rilevato.",
                        style={"color": "#94a3b8", "fontSize": "13px"})
    rows = []
    for s in sensors:
        rows.append(html.Div(
            [
                html.Span(s["sensor_id"], style={"fontFamily": "monospace", "fontSize": "12px",
                                                  "color": "#374151", "marginRight": "8px"}),
                html.Span("NUOVO", className="mm-badge-new"),
                html.Button(
                    "Accetta",
                    id={"type": "accept-sensor-btn", "id": s["sensor_id"]},
                    n_clicks=0,
                    style={"marginLeft": "12px", "background": "#0f172a", "color": "#fff",
                           "border": "none", "borderRadius": "6px", "padding": "3px 10px",
                           "fontSize": "11px", "cursor": "pointer"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "padding": "6px 0",
                   "borderBottom": "1px solid #f1f5f9"},
        ))
    return rows


@callback(
    Output("zones-threshold-list", "children"),
    Input("interval-60s", "n_intervals"),
    Input("settings-tabs", "active_tab"),
)
def update_zones_list(n, active_tab):
    if active_tab != "tab-thresholds":
        return no_update
    zones, err = _safe_get("/api/zones")
    if err or not zones:
        return html.Div("Nessuna zona configurata.", style={"color": "#94a3b8"})
    rows = []
    for z in zones:
        color = z.get("color", "#64748b")
        t_min = z.get("threshold_min", -30)
        t_max = z.get("threshold_max", 30)
        # Slider range: estendere di 5°C ai bordi per dare spazio di editing
        slider_min = t_min - 10
        slider_max = t_max + 10
        rows.append(html.Div(
            [
                html.Div(
                    [
                        html.Span("■", style={"color": color, "marginRight": "8px"}),
                        html.Span(z["name"], style={"fontWeight": "600", "fontSize": "13px", "flex": 1}),
                        html.Button(
                            "🗑",
                            id={"type": "delete-zone-btn", "name": z["name"]},
                            n_clicks=0,
                            title="Elimina zona",
                            style={"background": "none", "border": "none", "cursor": "pointer",
                                   "fontSize": "14px", "color": "#ef4444"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
                ),
                # RangeSlider per soglie min/max
                dcc.RangeSlider(
                    id={"type": "zone-threshold-slider", "name": z["name"]},
                    min=slider_min, max=slider_max, step=0.5,
                    value=[t_min, t_max],
                    marks={slider_min: f"{slider_min}°C", 0: "0°C", slider_max: f"{slider_max}°C"},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
                html.Div(id={"type": "zone-threshold-save-result", "name": z["name"]},
                         style={"fontSize": "11px", "marginTop": "4px"}),
            ],
            className="mm-card",
            style={"marginBottom": "12px", "borderLeft": f"4px solid {color}"},
        ))
    return rows


@callback(
    Output({"type": "zone-threshold-save-result", "name": MATCH}, "children"),
    Input({"type": "zone-threshold-slider", "name": MATCH}, "value"),
    State({"type": "zone-threshold-slider", "name": MATCH}, "id"),
    prevent_initial_call=True,
)
def save_zone_threshold(slider_value, slider_id):
    zone_name = slider_id["name"]
    min_val, max_val = slider_value
    # Fetch the current zone color before saving to avoid overwriting it
    zones, err_get = _safe_get("/api/zones")
    current_color = "#64748b"
    if zones:
        match = next((z for z in zones if z["name"] == zone_name), None)
        if match:
            current_color = match.get("color", "#64748b")
    result, err = _safe_post("/api/zones", json={
        "name": zone_name, "color": current_color,
        "threshold_min": min_val, "threshold_max": max_val,
    })
    if err:
        return html.Span(f"Errore: {err}", style={"color": "#ef4444"})
    return html.Span(f"✓ Salvato ({min_val}°C – {max_val}°C)", style={"color": "#22c55e"})
```

- [ ] **Step 2b: Aggiungere callback per sensori configurati e modali**

Aggiungere in `settings_callbacks.py`:

```python
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import dcc

# --- Tab Sensori: griglia sensori configurati ---
@callback(
    Output("configured-sensors-grid", "children"),
    Input("interval-60s", "n_intervals"),
    Input("settings-tabs", "active_tab"),
)
def update_configured_sensors(n, active_tab):
    if active_tab != "tab-sensors":
        return no_update
    sensors, err = _safe_get("/api/sensors")
    if err or not sensors:
        return html.Div("Nessun sensore configurato.", style={"color": "#94a3b8"})
    row_data = [{"id": s["id"], "name": s.get("name", ""), "zone": s.get("zone", ""),
                 "active": s.get("active", True)} for s in sensors]
    return dag.AgGrid(
        id="sensors-ag-grid",
        rowData=row_data,
        columnDefs=[
            {"field": "id",     "headerName": "ID",     "width": 140},
            {"field": "name",   "headerName": "Nome",   "flex": 1, "editable": True},
            {"field": "zone",   "headerName": "Zona",   "width": 120, "editable": True},
            {"field": "active", "headerName": "Attivo", "width": 90,
             "cellRenderer": "agCheckboxCellRenderer", "editable": True},
        ],
        className="ag-theme-quartz",
        style={"height": "300px"},
    )


# --- Modal: Accetta sensore scoperto ---
@callback(
    Output("accept-sensor-modal-container", "children"),
    Input({"type": "accept-sensor-btn", "id": ALL}, "n_clicks"),
    State({"type": "accept-sensor-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def open_accept_modal(n_clicks_list, btn_ids):
    if not any(n for n in n_clicks_list if n):
        return no_update
    triggered_idx = next(i for i, n in enumerate(n_clicks_list) if n)
    sensor_id = btn_ids[triggered_idx]["id"]

    modal = dbc.Modal(
        [
            dbc.ModalHeader(f"Accetta sensore: {sensor_id}"),
            dbc.ModalBody([
                html.Label("Nome", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="accept-sensor-name", type="text",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Zona", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="accept-sensor-zone", type="text",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Soglia min (opzionale)", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="accept-sensor-min", type="number",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Soglia max (opzionale)", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="accept-sensor-max", type="number",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px"}),
                dcc.Store(id="accept-sensor-id-store", data=sensor_id),
            ]),
            dbc.ModalFooter([
                dbc.Button("Annulla", id="accept-cancel-btn", color="secondary", size="sm"),
                dbc.Button("Accetta", id="accept-confirm-btn", color="primary", size="sm"),
            ]),
        ],
        id="accept-sensor-modal",
        is_open=True,
    )
    return modal


@callback(
    Output("accept-sensor-modal", "is_open"),
    Output("discovered-sensors-list", "children", allow_duplicate=True),
    Input("accept-confirm-btn", "n_clicks"),
    Input("accept-cancel-btn", "n_clicks"),
    State("accept-sensor-id-store", "data"),
    State("accept-sensor-name", "value"),
    State("accept-sensor-zone", "value"),
    State("accept-sensor-min", "value"),
    State("accept-sensor-max", "value"),
    prevent_initial_call=True,
)
def confirm_accept_sensor(confirm, cancel, sensor_id, name, zone, min_val, max_val):
    if ctx.triggered_id == "accept-cancel-btn":
        return False, no_update
    if not name or not zone:
        return True, no_update  # Keep modal open
    body = {"name": name, "zone": zone}
    if min_val is not None:
        body["min"] = min_val
    if max_val is not None:
        body["max"] = max_val
    _safe_post(f"/api/sensors/{sensor_id}/accept", json=body)
    return False, html.Div("Sensore accettato. Ricarica per aggiornare.",
                            style={"color": "#22c55e", "fontSize": "12px"})


# --- Modal: Aggiungi zona ---
@callback(
    Output("zone-modal-container", "children"),
    Input("add-zone-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_add_zone_modal(n):
    modal = dbc.Modal(
        [
            dbc.ModalHeader("Aggiungi zona"),
            dbc.ModalBody([
                html.Label("Nome zona", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-name", type="text",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Colore", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-color", type="text", value="#64748b",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Soglia min (°C)", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-min", type="number",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px", "marginBottom": "10px"}),
                html.Label("Soglia max (°C)", style={"fontSize": "12px", "fontWeight": "600"}),
                dcc.Input(id="new-zone-max", type="number",
                          style={"width": "100%", "padding": "6px", "border": "1px solid #e2e8f0",
                                 "borderRadius": "6px"}),
            ]),
            dbc.ModalFooter([
                dbc.Button("Annulla", id="zone-modal-cancel", color="secondary", size="sm"),
                dbc.Button("Crea zona", id="zone-modal-confirm", color="primary", size="sm"),
            ]),
        ],
        id="add-zone-modal",
        is_open=True,
    )
    return modal


@callback(
    Output("add-zone-modal", "is_open"),
    Output("zones-threshold-list", "children", allow_duplicate=True),
    Input("zone-modal-confirm", "n_clicks"),
    Input("zone-modal-cancel", "n_clicks"),
    State("new-zone-name", "value"),
    State("new-zone-color", "value"),
    State("new-zone-min", "value"),
    State("new-zone-max", "value"),
    prevent_initial_call=True,
)
def confirm_add_zone(confirm, cancel, name, color, min_val, max_val):
    if ctx.triggered_id == "zone-modal-cancel":
        return False, no_update
    if not name or min_val is None or max_val is None:
        return True, no_update
    _safe_post("/api/zones", json={
        "name": name, "color": color or "#64748b",
        "threshold_min": min_val, "threshold_max": max_val,
    })
    return False, html.Div("Zona aggiunta. Ricarica per aggiornare.",
                            style={"color": "#22c55e", "fontSize": "12px"})


# --- Delete zona ---
@callback(
    Output("zones-threshold-list", "children", allow_duplicate=True),
    Input({"type": "delete-zone-btn", "name": ALL}, "n_clicks"),
    State({"type": "delete-zone-btn", "name": ALL}, "id"),
    prevent_initial_call=True,
)
def delete_zone(n_clicks_list, btn_ids):
    if not any(n for n in n_clicks_list if n):
        return no_update
    triggered_idx = next(i for i, n in enumerate(n_clicks_list) if n)
    zone_name = btn_ids[triggered_idx]["name"]
    result, err = _safe_delete(f"/api/zones/{zone_name}")
    if err and "409" in str(err):
        return html.Div(f"Impossibile eliminare: {err}",
                        style={"color": "#ef4444", "fontSize": "12px"})
    # Force refresh
    return no_update
```

- [ ] **Step 3: Verificare navigazione a /impostazioni**

Aprire http://localhost:8050/impostazioni — verificare 5 tab visibili e cliccabili.

- [ ] **Step 4: Commit**

```bash
git add frontend/pages/settings.py frontend/callbacks/settings_callbacks.py
git commit -m "[feat] impostazioni v2: 5 tab, sensor discovery, add/delete zona"
```

---

## Task 9: Storico e Allarmi Aggiornati

**Files:**
- Modify: `frontend/pages/history.py`
- Modify: `frontend/callbacks/history_callbacks.py`
- Modify: `frontend/pages/alerts.py`
- Modify: `frontend/callbacks/alerts_callbacks.py`

- [ ] **Step 1: Aggiornare `frontend/pages/alerts.py`** — ag-theme-quartz + row coloring

Trovare il componente `dag.AgGrid` e aggiornare:

```python
dag.AgGrid(
    id="alerts-grid",
    className="ag-theme-quartz",  # era ag-theme-alpine-dark
    columnDefs=[
        {"field": "timestamp",    "headerName": "Data/Ora",  "width": 150},
        {"field": "zone",         "headerName": "Zona",       "width": 120,
         "cellRenderer": "agGroupCellRenderer"},
        {"field": "sensor_id",    "headerName": "Sensore",    "width": 120},
        {"field": "temperature",  "headerName": "Temp (°C)",  "width": 100},
        {"field": "level",        "headerName": "Livello",    "width": 100},
        {"field": "duration_min", "headerName": "Durata",     "width": 90},
        {"field": "message",      "headerName": "Messaggio",  "flex": 1},
    ],
    rowClassRules={
        "alert-row-critical": "params.data.level === 'CRITICAL'",
        "alert-row-warning":  "params.data.level === 'WARNING'",
    },
    dashGridOptions={"pagination": True, "paginationPageSize": 25},
    style={"height": "500px"},
)
```

Aggiungere in `assets/custom.css`:
```css
.alert-row-critical { background: #fef2f2 !important; }
.alert-row-warning  { background: #fffbeb !important; }
```

- [ ] **Step 2: Aggiornare `frontend/callbacks/history_callbacks.py`** — statistiche % fuori soglia

Nel callback di ricerca storico, recuperare prima le soglie via `GET /api/zones`, poi calcolare % fuori range:

```python
# 1. Ottenere soglie per zona dalla API
zones_data, _ = _safe_get("/api/zones")  # list of {name, threshold_min, threshold_max, color}
zone_thresh_map = {z["name"]: (z["threshold_min"], z["threshold_max"])
                   for z in (zones_data or [])}

# 2. Per ogni zona selezionata, calcolare statistiche
for zone_name in selected_zones:
    zone_readings = [r for r in readings if r.get("zone") == zone_name]
    threshold_min, threshold_max = zone_thresh_map.get(zone_name, (None, None))

    total = len(zone_readings)
    out_of_range = 0
    if threshold_min is not None and threshold_max is not None:
        out_of_range = sum(
            1 for r in zone_readings
            if r["temperature"] < threshold_min or r["temperature"] > threshold_max
        )
    pct_out = (out_of_range / total * 100) if total > 0 else 0.0

    # Aggiungere al layout statistiche:
    stats_block = html.Div([
        html.Div(f"Media: {sum(r['temperature'] for r in zone_readings)/total:.1f}°C" if total else "–"),
        html.Div(f"Min: {min(r['temperature'] for r in zone_readings):.1f}°C" if total else "–"),
        html.Div(f"Max: {max(r['temperature'] for r in zone_readings):.1f}°C" if total else "–"),
        html.Div(f"Letture: {total}"),
        html.Div(
            f"% tempo fuori soglia: {pct_out:.1f}%",
            style={"color": "#ef4444" if pct_out > 5 else "#22c55e", "fontWeight": "600"}
        ),
    ])
```

- [ ] **Step 3: Aggiornare tema Plotly nei grafici**

In `frontend/components/charts.py` (o ovunque siano definiti i grafici):

```python
fig.update_layout(
    template="plotly_white",  # era plotly_dark
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font_color="#0f172a",
)
```

- [ ] **Step 4: Verificare pagine**

Aprire /storico e /allarmi — verificare light theme, nessun crash.

- [ ] **Step 5: Commit**

```bash
git add frontend/pages/alerts.py frontend/callbacks/alerts_callbacks.py \
        frontend/pages/history.py frontend/callbacks/history_callbacks.py \
        frontend/assets/custom.css
git commit -m "[feat] storico/allarmi v2: ag-theme-quartz, row coloring, % fuori soglia, light theme"
```

---

## Task 10: Robustezza Backend

**Files:**
- Modify: `backend/routers/readings.py`
- Modify: `backend/routers/alerts.py`
- Modify: `backend/routers/sensors.py` (endpoint esistenti)
- Modify: `backend/routers/config.py` (endpoint esistenti)
- Modify: `backend/routers/thresholds.py`
- Modify: `backend/services/alert_service.py` — catch in job

- [ ] **Step 1: Aggiungere try/except strutturato a tutti i router esistenti**

Pattern da applicare a ogni endpoint `@router.get/post/patch/delete` in tutti i router:

```python
from fastapi import HTTPException

@router.get("/api/readings")
async def get_readings(...):
    try:
        # ... logica esistente ...
    except HTTPException:
        raise  # re-raise FastAPI exceptions as-is
    except Exception as e:
        logger.error("get_readings failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
```

Applicare a: `readings.py` (tutti gli endpoint), `alerts.py` (tutti), `config.py` (tutti), `thresholds.py` (tutti), `sensors.py` (endpoint esistenti non già wrappati in Task 5).

- [ ] **Step 2: Aggiungere catch nelle eccezioni dei job APScheduler**

In `backend/services/alert_service.py`, nel metodo `check_alerts`:

```python
async def check_alerts(self):
    try:
        # ... logica esistente ...
    except Exception as e:
        logger.error("alert_service.check_alerts failed: %s", e, exc_info=True)
        # Non rilancia — APScheduler logga ma non crasha
```

- [ ] **Step 3: Aggiungere validazione schema a `PATCH /api/config`**

In `backend/routers/config.py`, prima di scrivere su disco:

```python
@router.patch("/api/config")
async def patch_config(patch: ConfigPatch):
    try:
        # Applica il patch
        updated = config_service.apply_patch(patch)
        # Validazione: il risultato deve essere un AppConfig valido
        AppConfig.model_validate(updated.model_dump())
        return updated
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Config validation failed: {e}")
    except Exception as e:
        logger.error("patch_config failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Eseguire i test**

```bash
pytest backend/tests/ -v
```
Expected: tutti PASS (nessuna regressione)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ backend/services/alert_service.py
git commit -m "[feat] robustezza backend: try/except in tutti i router, catch job APScheduler, validazione PATCH config"
```

---

## Task 10b: Robustezza Frontend

**Files:**
- Modify: tutti i file `frontend/callbacks/*.py`

- [ ] **Step 1: Wrappare tutti i callback rimasti in try/except**

Per ogni callback che fa chiamate API e non ha già il wrapping `_safe_get`, verificare e aggiungere:

```python
try:
    # ... logica callback
except Exception as e:
    return html.Div(
        f"Errore: {str(e)}",
        style={"color": "#ef4444", "padding": "8px", "fontSize": "12px"},
    )
```

Pattern helper da aggiungere in `frontend/utils.py` (se non esiste):

```python
"""Utility helpers per i callback frontend."""

import requests

API_BASE = "http://localhost:8000"

def safe_get(path: str, timeout: int = 3):
    """GET con gestione errori. Returns (data, error_str)."""
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Backend non raggiungibile"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def safe_post(path: str, json=None, timeout: int = 5):
    """POST con gestione errori. Returns (data, error_str)."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Backend non raggiungibile"
    except Exception as e:
        return None, str(e)
```

- [ ] **Step 2: Aggiornare i callback per usare `safe_get`/`safe_post` da utils**

In ogni callback file, sostituire le definizioni locali `_safe_get`/`_safe_post` con import da `frontend.utils`.

- [ ] **Step 3: Verificare che il frontend non crashi con backend spento**

Spegnere il backend, aprire ogni pagina — ogni pagina deve mostrare messaggio di errore graceful.

- [ ] **Step 4: Commit**

```bash
git add frontend/utils.py frontend/callbacks/
git commit -m "[feat] robustezza frontend: wrapping try/except, utils.safe_get/post centralizzati"
```

---

## Task 11: Archive Service

**Files:**
- Create: `backend/services/archive_service.py`
- Create: `backend/routers/archive.py`
- Modify: `backend/main.py` — job archive già aggiunto in Task 4
- Modify: `backend/database/tinyflux_adapter.py` — implementa delete_readings/alerts_before

- [ ] **Step 1: Scrivere test per archive service**

```python
# backend/tests/test_archive_service.py
import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_archive_creates_csv(tmp_path, monkeypatch):
    """Archive service deve creare CSV e aggiornare archive_log.json."""
    from backend.services.archive_service import ArchiveService

    # Mock DB adapter
    mock_db = AsyncMock()
    mock_db.get_readings.return_value = [
        {"timestamp": (datetime.now(tz=timezone.utc) - timedelta(days=200)).isoformat(),
         "zone": "fridge", "sensor_id": "SEN-001", "temperature": 4.2,
         "humidity": None, "battery": 87},
    ]
    mock_db.get_alerts.return_value = []
    mock_db.delete_readings_before = AsyncMock(return_value=1)
    mock_db.delete_alerts_before = AsyncMock(return_value=0)

    # Mock config service
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
```

- [ ] **Step 2: Eseguire il test — deve fallire**

```bash
pytest backend/tests/test_archive_service.py -v
```
Expected: FAIL (modulo non esiste)

- [ ] **Step 3: Creare `backend/services/archive_service.py`**

```python
"""Archive service — export readings/alerts to CSV, then purge from DB."""

import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.paths import data_file

logger = logging.getLogger(__name__)

ARCHIVE_DIR = data_file("archive")


class ArchiveService:
    def __init__(self, db, config_service):
        self._db = db
        self._config = config_service

    async def run(self) -> dict:
        cfg = self._config.get_config()
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=cfg.archive_after_days)

        logger.info("Archive: cutoff=%s", cutoff.isoformat())

        # Fetch data to archive.
        # IMPORTANT: Before coding, read backend/database/adapter.py to verify the exact
        # signature of get_readings() and get_alerts().
        # Expected: get_readings(zone, sensor_id, from_dt, to_dt, limit) — use to_dt=cutoff.
        # For get_alerts, check if it accepts to_dt or a different param name.
        # Adjust the calls below to match the actual adapter signature:
        readings = await self._db.get_readings(
            zone=None, sensor_id=None, from_dt=None, to_dt=cutoff, limit=None
        )
        # get_alerts signature may differ — check adapter.py and adjust:
        alerts = await self._db.get_alerts(to_dt=cutoff)

        rows_archived = 0
        files_written = []

        # Group by YYYY-MM
        def _month_key(ts_str: str) -> str:
            return ts_str[:7]  # "YYYY-MM"

        readings_by_month = defaultdict(list)
        for r in readings:
            readings_by_month[_month_key(r["timestamp"])].append(r)

        alerts_by_month = defaultdict(list)
        for a in alerts:
            alerts_by_month[_month_key(a["timestamp"])].append(a)

        all_months = set(readings_by_month) | set(alerts_by_month)

        for month in sorted(all_months):
            month_dir = Path(ARCHIVE_DIR) / month
            month_dir.mkdir(parents=True, exist_ok=True)

            # Readings CSV
            if readings_by_month[month]:
                path = month_dir / "readings.csv"
                _write_csv(
                    path,
                    readings_by_month[month],
                    ["timestamp", "zone", "sensor_id", "temperature", "humidity", "battery"],
                )
                files_written.append(str(path))
                rows_archived += len(readings_by_month[month])

            # Alerts CSV
            if alerts_by_month[month]:
                path = month_dir / "alerts.csv"
                _write_csv(
                    path,
                    alerts_by_month[month],
                    ["timestamp", "zone", "sensor_id", "temperature", "level", "message", "resolved"],
                )
                files_written.append(str(path))
                rows_archived += len(alerts_by_month[month])

        # Purge from DB
        if readings:
            await self._db.delete_readings_before(cutoff)
        if alerts:
            await self._db.delete_alerts_before(cutoff)

        # Update archive log
        log_path = Path(ARCHIVE_DIR) / "archive_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_data = {
            "last_run": datetime.now(tz=timezone.utc).isoformat(),
            "last_rows_archived": rows_archived,
            "files": files_written,
        }
        log_path.write_text(json.dumps(log_data, indent=2), encoding="utf-8")

        logger.info("Archive complete: %d rows archived, %d files", rows_archived, len(files_written))
        return {"status": "completed", "rows_archived": rows_archived, "files_written": files_written}

    def get_status(self) -> dict:
        log_path = Path(ARCHIVE_DIR) / "archive_log.json"
        base = {"last_run": None, "last_rows_archived": 0,
                "archive_dir": str(ARCHIVE_DIR), "files": []}
        if log_path.exists():
            try:
                return {**base, **json.loads(log_path.read_text(encoding="utf-8"))}
            except Exception:
                pass
        return base


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    """Write rows to CSV, appending if file exists (preserves data on repeated runs).
    Header is written only if the file does not already exist.
    """
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
```

- [ ] **Step 4: Eseguire il test — deve passare**

```bash
pytest backend/tests/test_archive_service.py -v
```
Expected: PASS

- [ ] **Step 5: Creare `backend/routers/archive.py`**

```python
"""Archive endpoints."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/archive", tags=["archive"])


@router.get("/status")
async def archive_status():
    from backend.services.archive_service import ArchiveService
    from backend.dependencies import get_db
    from backend.services.config_service import config_service
    svc = ArchiveService(db=get_db(), config_service=config_service)
    return svc.get_status()


@router.post("/run")
async def archive_run():
    from backend.services.archive_service import ArchiveService
    from backend.dependencies import get_db
    from backend.services.config_service import config_service
    svc = ArchiveService(db=get_db(), config_service=config_service)
    return await svc.run()
```

- [ ] **Step 6: Registrare archive router in `backend/main.py`**

```python
from backend.routers import archive as archive_router
# ...
app.include_router(archive_router.router)
```

- [ ] **Step 7: Eseguire tutti i test**

```bash
pytest backend/tests/ -v
```
Expected: tutti PASS

- [ ] **Step 8: Commit**

```bash
git add backend/services/archive_service.py backend/routers/archive.py \
        backend/main.py backend/tests/test_archive_service.py
git commit -m "[feat] archive service: export CSV + purge DB + job 02:00 + GET/POST /api/archive"
```

---

## Task 12: Test

**Files:**
- Modify: `backend/tests/`

- [ ] **Step 1: Verificare copertura test esistenti**

```bash
pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```

- [ ] **Step 2: Aggiungere test per robustezza backend**

```python
# backend/tests/test_robustness.py
def test_health_no_crash_without_mqtt(test_client):
    """GET /api/health non crasha se mqtt_client è None."""
    r = test_client.get("/api/health")
    assert r.status_code == 200

def test_logs_empty_without_collector(test_client):
    """GET /api/logs restituisce [] se log_collector non è in app.state."""
    r = test_client.get("/api/logs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_zones_get(test_client):
    """GET /api/zones restituisce lista."""
    r = test_client.get("/api/zones")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_sensor_discovered_empty(test_client):
    """GET /api/sensors/discovered restituisce [] con MQTT inattivo."""
    r = test_client.get("/api/sensors/discovered")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_archive_status_no_crash(test_client):
    """GET /api/archive/status non crasha se archive_log.json non esiste."""
    r = test_client.get("/api/archive/status")
    assert r.status_code == 200
    data = r.json()
    assert "last_run" in data
```

- [ ] **Step 3: Eseguire tutti i test**

```bash
pytest backend/tests/ -v
```
Expected: tutti PASS

- [ ] **Step 4: Commit finale**

```bash
git add backend/tests/
git commit -m "[test] test suite v2: health, logs, zones, sensors/discovered, archive"
```

---

## Verifica finale

- [ ] **Avviare backend e frontend**

```bash
# Terminale 1
uvicorn backend.main:app --reload --port 8000

# Terminale 2
python frontend/app.py
```

- [ ] **Smoke test manuale** — aprire ogni pagina:
  - `/` — Dashboard: zone cards, sensors table, chart
  - `/storico` — filtri, export CSV
  - `/allarmi` — ag-theme-quartz, filtri
  - `/impostazioni` — 5 tab, sensor discovery
  - `/sistema` — service cards, log panel, metriche, archivia ora

- [ ] **Test resilienza** — spegnere backend, aprire ogni pagina — nessun crash, messaggio errore visibile

- [ ] **Creare PR**

```bash
git push origin feature/ui-redesign-v2
gh pr create --base master --title "[feat] medMonitor v2 — UI Redesign + Robustezza + Archive" \
  --body "Redesign completo UI: Modern SaaS Light, pagina Sistema, sensor discovery, archive CSV."
```
