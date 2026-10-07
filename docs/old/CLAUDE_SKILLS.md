# Claude Skills — medMonitor

Modello: **claude-opus-4-6** per tutte le fasi.

## Skill 1 — Backend FastAPI
Router modulari, Pydantic v2, asyncpg, logging strutturato.
DatabaseAdapter iniettato via Depends(). Config gerarchica pydantic-settings.

Struttura:
```
backend/
├── main.py
├── config.py
├── database/
│   ├── adapter.py          # ABC DatabaseAdapter
│   ├── factory.py          # get_adapter(settings)
│   ├── tinyflux_adapter.py
│   ├── timescale_adapter.py
│   └── migrations/
├── models/
├── routers/
│   ├── readings.py
│   ├── alerts.py
│   ├── sensors.py
│   ├── thresholds.py
│   ├── config.py
│   └── demo.py
└── services/
    ├── mqtt_client.py
    ├── alert_service.py
    ├── email_service.py
    ├── imap_service.py
    ├── config_service.py
    └── demo_generator.py
```

## Skill 2 — Database Abstraction Layer
Classe astratta con metodi: write_reading, get_readings, get_latest,
write_alert, get_alerts, delete_demo_data.
TinyFluxAdapter e TimescaleAdapter intercambiabili via factory.

## Skill 3 — MQTT ZigBee
Paho-MQTT, subscribe zigbee2mqtt/#, reconnect esponenziale (1→2→4→max 60s).
Parsing JSON, identificazione zona da DB sensori.

## Skill 4 — Frontend Plotly Dash
dash + dash-bootstrap-components + plotly + dash-iconify + dash-ag-grid.
Tema SLATE (dark) default, selezionabile da UI.
Pattern MATCH per gestire N sensori dinamicamente nei callback.

## Skill 5 — Config Service
Lettura gerarchica: default → .env → config.json.
Hot reload soglie e email senza riavvio.
Switch database con migrazione opzionale e progress bar.

## Skill 6 — Alert Service
APScheduler ogni minuto. Livelli WARNING (0-15 min) e CRITICAL (>15 min).
Cooldown configurabile. Template Jinja2 HTML. aiosmtplib asincrono per SMTP.
aioimaplib per monitoraggio IMAP (conferme operatore, comandi via email).

## Skill 7 — Docker
docker-compose con mosquitto, backend, frontend.
PostgreSQL come profilo opzionale (profile: timescale).
Volume ./data:/app/data per TinyFlux e config.json.

## Skill 8 — Demo Mode
DemoGenerator: mean reversion + gauss(0, sigma) + drift scenario.
6 scenari, asyncio.create_task, sensor_id prefisso 0xDEMO.
Banner dbc.Alert giallo in tutte le pagine quando demo attiva.

## Skill 9 — Soglie per sensore
ThresholdsConfig: defaults (zona) + sensors (override individuale).
Metodo resolve(sensor_id) → (effective_min, effective_max).
Alert service usa resolve() per ogni sensore.
UI: dbc.Switch + dcc.RangeSlider + Input sincronizzati con MATCH callback.
Icona ★ in zone card se override=True.
Bande add_hrect nel grafico storico per ogni sensore.

## Dipendenze Python complete
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.0
pydantic-settings==2.2.1
asyncpg==0.29.0
tinyflux==1.1.0
paho-mqtt==2.0.0
apscheduler==3.10.4
aiosmtplib==3.0.1
aioimaplib==1.1.0
jinja2==3.1.4
dash==2.17.0
dash-bootstrap-components==1.6.0
plotly==5.22.0
dash-iconify==0.1.6
dash-ag-grid==31.2.0
requests==2.32.0
pytest==8.2.0
pytest-asyncio==0.23.7
```