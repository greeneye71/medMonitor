# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**medMonitor** is a ZigBee temperature monitoring system for refrigerated storage (fridges/freezers) with automated email alerts. This is a specification-driven project — documentation files define the full system architecture and implementation plan.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, APScheduler, Paho-MQTT
- **Database:** TinyFlux (dev/small) or PostgreSQL + TimescaleDB (production)
- **Frontend:** Plotly Dash, Dash Bootstrap Components, Dash-AG-Grid
- **Alerts:** aiosmtplib (SMTP) + aioimaplib (IMAP) + Jinja2 HTML templates
- **Deployment:** Windows nativo / Docker Compose

## Build & Run Commands

```bash
# === Windows nativo ===
# Setup ambiente
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Backend dev server
uvicorn backend.main:app --reload --port 8000

# Frontend dev server (terminale separato)
python frontend/app.py

# Mosquitto: installa come servizio Windows da https://mosquitto.org/download/

# === Docker Compose ===
docker compose up -d
docker compose --profile timescale up -d   # con TimescaleDB

# === Test ===
pytest backend/tests/ -v --cov=backend
pytest backend/tests/test_api.py -v
```

**Ports:** MQTT 1883, Backend/API 8000 (/docs for Swagger), Frontend 8050

## Architecture

```
ZigBee Sensors → Gateway → MQTT Broker → FastAPI Backend
  → DatabaseAdapter (TinyFlux or TimescaleDB) → Plotly Dash Frontend
```

### Key Design Patterns

- **Database Abstraction Layer:** Abstract `DatabaseAdapter` with TinyFlux and TimescaleDB implementations. Factory pattern via `get_adapter(settings)` based on `DATABASE_BACKEND` env var. Both adapters share the same interface — all tests must pass against both.
- **Threshold Resolution:** Hierarchical — zone defaults → sensor-specific overrides. `ThresholdsConfig.resolve(sensor_id)` returns effective `(min, max)`.
- **Configuration Hierarchy:** Hardcoded defaults (config.py) < `.env` file < `data/config.json` (UI modifications, hot reloaded).
- **Alert Service:** APScheduler checks every 60s. Two levels: WARNING (0-15 min out of range), CRITICAL (>15 min). Cooldown default 30 min. SMTP for sending, IMAP for operator confirmations (ACK, MUTE, ESCALATE).
- **MQTT Client:** Paho-MQTT subscribing to `zigbee2mqtt/#` with exponential backoff reconnect (1s → max 60s).

### Frontend Pages (Italian UI)

1. **Dashboard** — Real-time gauges, zone cards, 24h history
2. **Storico** — Date range history, CSV export, statistics
3. **Allarmi** — AG Grid alert table with filtering
4. **Impostazioni** — Settings (7 tabs: General, Thresholds, Sensors, Email, Database, System, Demo)

**Design system:** SLATE theme (dark), semantic colors: OK `#1D9E75`, WARNING `#BA7517`, CRITICAL `#E24B4A`.

## Implementation Phases

The project follows 11 phases defined in `CLAUDE_PROMPTS.md`, each with a dedicated git branch. Commit messages use prefixes: `[feat]`, `[fix]`, `[docs]`, `[test]`, `[refactor]`.

## Specification Documents

- `ARCHITECTURE.md` — System diagram and data flow
- `API.md` — Complete REST API specification
- `DATABASE_ADAPTER.md` — Adapter pattern and migration strategy
- `CONFIGURATION.md` — Config hierarchy and environment variables
- `ALERTS.md` — Alert logic and email templates
- `UI_DESIGN.md` — Frontend design system and component specs
- `DEMO_MODE.md` — 6 demo scenarios with physical simulation model
- `HARDWARE.md` — Gateway and sensor recommendations
- `INSTALLATION.md` — Deployment guide
- `CLAUDE_PROMPTS.md` — 11 implementation prompts (phases)
- `CLAUDE_SKILLS.md` — 9 AI development skills
- `CLAUDE_WORKFLOW.md` — Git workflow and branch conventions

## Key Environment Variables

```
DATABASE_BACKEND=tinyflux|timescale
MQTT_HOST, MQTT_PORT
ZIGBEE_GATEWAY_IP
SMTP_HOST, SMTP_PORT, SMTP_USE_TLS, SMTP_USER, SMTP_PASSWORD, ALERT_RECIPIENTS
IMAP_HOST, IMAP_PORT, IMAP_USE_SSL, IMAP_USER, IMAP_PASSWORD, IMAP_FOLDER
ALERT_COOLDOWN_MINUTES=30
POLLING_INTERVAL_MINUTES=10
```
