# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**medMonitor v2**: temperature monitoring for fridges/freezers with Zigbee sensors and
email alerts. Runs on a Fedora VM with Podman rootless + Quadlet. Keep things simple:
one Python app, SQLite, no frontend build step. UI and docs are in Italian.

Design spec: `docs/superpowers/specs/2026-10-08-fedora-v2-design.md`.
Installation guide (also meant to be followed by Claude Code on the server): `INSTALL.md`.
v1 docs (Dash, TinyFlux/TimescaleDB, Windows) are obsolete and live in `docs/old/`.

## Architecture

```
SNZB-02LD → SONOFF Dongle-M (Ethernet, tcp://IP:6638, adapter ember)
  → zigbee2mqtt → mosquitto → medmonitor (FastAPI) → SQLite + monthly CSV archive
```

Multi-gateway (v2.1): one Dongle-M per environment ("ambiente"), each with its own zigbee2mqtt
container and Zigbee network, all on one mosquitto. Registry `DATA_DIR/gateways.json`
(`{"gateways":[{id,name,base_topic,config,frontend_port}],"next_id":N}`), written by `install.sh`;
the app only rewrites names. Gateway 1: container `zigbee2mqtt`, dir `z2m`, topic `zigbee2mqtt`,
port 8080. Gateway n≥2: `zigbee2mqtt-n`, `z2m-n`, `zigbee2mqtt_n`, port 8079+n (skipping used ports).
Ids never reused. Missing registry = single gateway from `Z2M_CONFIG`. `sensors.gateway_id`
and `discovered.gateway_id` default 1. With one gateway UI and emails look like v2.0.

- `app/main.py` — `create_app(data_dir, start_services, z2m_path)` factory; scheduler jobs:
  sampling cron `*/10`, email outbox every minute, archive daily 03:00, VACUUM Sunday 03:30.
- `app/gateways.py` — loads/saves `gateways.json` (`load(dir, fallback_config)`).
- `app/mqtt.py` — per gateway subscribes `<base>/+` and `<base>/bridge/{devices,state,info}`, stores last reading per sensor, per-gateway bridge state, pairing (permit_join), discovered devices, sensor move between gateways.
- `app/monitor.py` — sampling + alarm rules (N consecutive out-of-range, offline, low battery, gateway offline with sensor-offline email suppression).
- `app/notifier.py` — email outbox, SMTP via aiosmtplib, retries; failures logged as `EMAIL_ERROR` events.
- `app/archive.py` — moves samples older than retention to `archive/YYYY-MM.csv`.
- `app/settings.py` — settings stored as JSON in SQLite (`alarm`, `archive`, `smtp`, …) with defaults.
- `app/z2m_config.py` — reads/writes gateway IP and channel in a zigbee2mqtt `configuration.yaml` (by path, one per gateway).
- `app/web/` — Jinja2 + HTMX + ECharts (vendored, no CDN). Public: Panoramica, Storico, Eventi.
  Password-protected: Impostazioni (Sensori, Email, Gateway, Allarmi, Archivio, Sicurezza).

Environment: `DATA_DIR` (default `data`), `ADMIN_PASSWORD` (only sets the initial hash),
`MQTT_HOST`, `MQTT_PORT`, `Z2M_CONFIG`, `SECRET_KEY`, `UI_PORT` (container only).

## Commands

```bash
# Local tests (Windows dev machine)
.venv2/Scripts/python -m pytest -q

# Local run
DATA_DIR=data .venv2/Scripts/uvicorn app.main:create_app --factory --port 8090

# Server (Fedora): install or update
./install.sh
systemctl --user status medmonitor
journalctl --user -u medmonitor -f
```

## Rules

- UI port is chosen at install time, default **8090**. Never use port 8000.
- Deployment = `Containerfile` + `install.sh` (writes Quadlet units to `~/.config/containers/systemd/`).
  Data in `~/medmonitor-data/{app,z2m,z2m-n}`, config in `<repo>/.env` (Podman env-file: no inline comments).
  Gateways are added/removed only via the `install.sh` menu (the app container cannot create systemd units).
- Security is not a concern (protected VM): SMTP password stored in plain text is fine.
- Commit prefixes: `[feat]`, `[fix]`, `[docs]`, `[test]`, `[refactor]`. Never commit `.claude/settings.local.json`.
