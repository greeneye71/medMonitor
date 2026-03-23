#!/usr/bin/env python3
"""
Esegui nella cartella del progetto:
  python create_docs.py
"""
import os

files = {}

files["README.md"] = """# medMonitor

Sistema di monitoraggio temperatura per celle frigorifere e freezer,
con dashboard web professionale e notifiche email automatiche.

## Caratteristiche principali

- Acquisizione dati da sensori ZigBee tramite gateway Wi-Fi/Ethernet
- Logging ogni 10 minuti (TinyFlux o PostgreSQL + TimescaleDB)
- Dashboard Plotly Dash professionale (tema dark/light)
- Soglie configurabili individualmente per ogni sensore
- Sistema di allarme email WARNING / CRITICAL
- Modalità demo con 6 scenari simulati realistici
- Deploy locale con Docker Compose

## Stack tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | Python 3.11, FastAPI, APScheduler, Paho-MQTT |
| Database | TinyFlux (default) → TimescaleDB (scalabile) |
| Frontend | Plotly Dash + Dash Bootstrap Components |
| Hardware | Gateway ZigBee Wi-Fi (Sonoff ZBBridge Pro) |
| Email | SMTP (invio) + IMAP (ricezione/conferme) |
| Deploy | Windows nativo / Docker Compose |

## Avvio rapido
```bash
gh repo clone greeneye71/medMonitor
cd medMonitor
cp .env.example .env
# Modifica .env con le tue impostazioni
docker-compose up -d
```

Dashboard: http://localhost:8050
API docs:  http://localhost:8000/docs

## Modello AI

Sviluppato con **claude-opus-4-6** tramite Claude Code.
"""

files["ARCHITECTURE.md"] = """# Architettura del sistema

## Principio chiave: Database Abstraction Layer

Due database intercambiabili senza modificare il codice applicativo:
- **TinyFlux** — Python puro, zero infrastruttura, default iniziale
- **TimescaleDB** — PostgreSQL esteso, produzione, alta scalabilità

## Schema generale
```
[Sensori ZigBee]
      | ZigBee 2.4GHz
      v
[Gateway Wi-Fi/Ethernet]   Sonoff ZBBridge Pro / SLZB-06
      | MQTT TCP/IP LAN
      v
[Mosquitto MQTT Broker]    Docker
      | subscribe zigbee2mqtt/#
      v
[Backend FastAPI]
      |              |
      |              | APScheduler ogni minuto
      |              v
      |         [Alert Engine] --> SMTP/SendGrid --> Email
      |
      | DatabaseAdapter (astratto)
      |_________________________
      |                         |
      v                         v
[TinyFlux]               [TimescaleDB]
file CSV locale           PostgreSQL+estensione
      |
      v
[Frontend Plotly Dash]    http://localhost:8050
```

## Database Abstraction Layer
```python
class DatabaseAdapter(ABC):
    async def write_reading(self, reading): ...
    async def get_readings(self, zone, from_dt, to_dt, limit): ...
    async def get_latest(self): ...
    async def write_alert(self, alert): ...
    async def get_alerts(self, limit): ...
    async def delete_demo_data(self): ...

# Factory: legge DATABASE_BACKEND da config
def get_adapter(settings) -> DatabaseAdapter:
    if settings.database_backend == "tinyflux":
        return TinyFluxAdapter(settings.tinyflux_path)
    return TimescaleAdapter(settings.postgres_dsn)
```

## Quando migrare a TimescaleDB

| Condizione | Azione |
|---|---|
| > 10 sensori attivi | Valutare migrazione |
| File TinyFlux > 500 MB | Pianificare migrazione |
| Query lente (> 2s) | Migrare |
| > 3 anni di dati | Migrare |

## Porte di rete

| Servizio | Porta |
|---|---|
| Dash frontend | 8050 |
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Mosquitto MQTT | 1883 |

## Stadi di scalabilità

- **Stadio 1**: TinyFlux, 2-5 sensori, 1 sede, Docker locale
- **Stadio 2**: TimescaleDB, 10-50 sensori, 1-3 sedi, VPS
- **Stadio 3**: InfluxDB/QuestDB, 100+ sensori, multi-sede, cloud
"""

files["HARDWARE.md"] = """# Hardware consigliato

## Gateway ZigBee

Poiché l'app gira su VM, si usa un gateway con connettività
Wi-Fi o Ethernet invece di un dongle USB.

### Sonoff ZBBridge Pro (consigliato) ~22 €
- Wi-Fi 2.4GHz, firmware nativo o Tasmota
- MQTT nativo, ZigBee 3.0, chip EFR32MG21

### SLZB-06 ~35 € (Ethernet, più stabile)
- Ethernet, open source, compatibile Zigbee2MQTT

## Sensori temperatura

### Frigorifero (0°C / +30°C)
- Sonoff SNZB-02D: ~14 €, -20/+60°C, ±0.5°C, display LCD
- MOES ZSS-ZK-THL: ~12 €, -10/+50°C, ±0.3°C

### Freezer (-30°C / 0°C)
- Aqara Temperature T1: ~16 €, -40/+85°C, ±0.3°C  ← consigliato
- Sonoff SNZB-02P: ~12 €, -40/+85°C, IP65

## Costo totale configurazione base

| Componente | Costo |
|---|---|
| Gateway Sonoff ZBBridge Pro | ~22 € |
| Sensore frigorifero (SNZB-02D) | ~14 € |
| Sensore freezer (Aqara T1) | ~16 € |
| **Totale** | **~52 €** |

## Requisiti VM

| Risorsa | Minimo | Consigliato |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB | 50 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
"""

files["INSTALLATION.md"] = """# Guida all'installazione

## 1. Prerequisiti
```bash
# Docker
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker

# GitHub CLI
sudo apt install -y gh
gh auth login
```

## 2. Clone e configurazione
```bash
gh repo clone greeneye71/medMonitor
cd medMonitor
cp .env.example .env
nano .env
```

Parametri minimi in .env:
```ini
DATABASE_BACKEND=tinyflux
TINYFLUX_PATH=./data/temperature.db
MQTT_HOST=mosquitto
ZIGBEE_GATEWAY_IP=192.168.1.100
SMTP_HOST=smtp.gmail.com
SMTP_USER=tua@email.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
ALERT_RECIPIENTS=destinatario@email.com
FRIDGE_TEMP_MIN=0.0
FRIDGE_TEMP_MAX=30.0
FREEZER_TEMP_MIN=-30.0
FREEZER_TEMP_MAX=0.0
```

## 3. Avvio
```bash
docker-compose up -d
docker-compose ps
```

## 4. Verifica

- Dashboard: http://localhost:8050
- API docs:   http://localhost:8000/docs

## 5. Test con modalità demo
```bash
curl -X POST http://localhost:8000/api/demo/start \\
  -H "Content-Type: application/json" \\
  -d '{"speed": "10x", "scenario": "full_stress"}'
```

Apri http://localhost:8050 — vedrai il banner demo giallo.

## 6. Backup
```bash
# TinyFlux
cp data/temperature.db backup_$(date +%Y%m%d).db

# TimescaleDB
docker-compose exec postgres pg_dump -U medmon medmonitor > backup_$(date +%Y%m%d).sql
```
"""

files["ALERTS.md"] = """# Configurazione allarmi e notifiche

## Soglie di temperatura

Ogni sensore ha soglie proprie. I nuovi sensori ereditano il default di zona.

| Zona | Min default | Max default |
|---|---|---|
| Frigorifero | 0°C | +30°C |
| Freezer | -30°C | 0°C |

> Modifica le soglie per sensore: Impostazioni > Soglie temperatura

## Livelli di allarme

| Livello | Condizione | Azione |
|---|---|---|
| WARNING | Fuori soglia 0-15 min | Email con oggetto [AVVISO] |
| CRITICAL | Fuori soglia > 15 min | Email ogni 30 min con oggetto [ALLARME CRITICO] |

## Configurazione email

### Gmail (App Password)
1. Account Google > Sicurezza > Password per le app
2. In .env:
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tuo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_RECIPIENTS=dest1@email.com,dest2@email.com
```

### SendGrid
```ini
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxxxxxxxxxxxxx
```

## Test email
```bash
curl -X POST http://localhost:8000/api/alerts/test \\
  -H "Content-Type: application/json" \\
  -d '{"email": "tuo@email.com"}'
```

## Cooldown

Default: 30 minuti tra email successive per la stessa zona.
Modificabile in .env: `ALERT_COOLDOWN_MINUTES=30`
"""

files["API.md"] = """# Documentazione API REST

Base URL: `http://localhost:8000/api`
Swagger UI: `http://localhost:8000/docs`

## Readings

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /readings | Letture con filtri (zone, from, to, limit) |
| GET | /readings/latest | Ultima lettura per ogni zona |

## Alerts

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /alerts | Storico allarmi |
| POST | /alerts/test | Invia email di test |

## Sensors

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /sensors | Lista sensori registrati |
| PUT | /sensors/{id} | Aggiorna nome/zona sensore |

## Thresholds (soglie per sensore)

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /thresholds | Defaults zona + soglie per sensore con effective_min/max |
| PATCH | /thresholds/defaults | Aggiorna default di zona |
| PATCH | /thresholds/sensor/{sensor_id} | Soglie individuali sensore |
| DELETE | /thresholds/sensor/{sensor_id} | Ripristina default zona |

Esempio PATCH soglie sensore:
```json
{ "min": -22.0, "max": -16.0, "override": true }
```

## Config

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /config | Configurazione completa |
| PATCH | /config | Aggiorna parametri runtime |
| POST | /config/test-email | Test SMTP |
| POST | /config/switch-database | Cambia backend DB |

## Demo

| Metodo | Endpoint | Descrizione |
|---|---|---|
| POST | /demo/start | Avvia demo (scenario, speed) |
| POST | /demo/stop | Ferma demo |
| GET | /demo/status | Stato corrente |
| POST | /demo/reset | Cancella dati demo |
"""

files["CHANGELOG.md"] = """# Changelog

## v0.5.0 — Soglie per sensore individuale
- Soglie min/max configurabili per ogni sensore separatamente
- Override attivabile singolarmente, eredita default zona se disattivato
- Indicatore ★ in dashboard per sensori con soglie personalizzate
- Bande soglia individuali nel grafico storico

## v0.4.0 — Demo mode
- 6 scenari: normal, fridge_alarm, freezer_alarm, power_loss,
  sensor_battery_low, full_stress
- Generatore fisico: mean reversion + rumore gaussiano + drift scenario
- Velocità configurabile: 1x / 10x / 60x / 600x
- Banner demo in UI, reset dati con un click

## v0.3.0 — Frontend completo
- Dashboard Plotly Dash con tema SLATE dark
- Pagine: Dashboard, Storico, Allarmi, Impostazioni
- Pannello configurazione completo con tabs

## v0.2.0 — Backend completo
- MQTT client con reconnect esponenziale automatico
- API REST FastAPI con tutti gli endpoint
- Alert service WARNING/CRITICAL con cooldown

## v0.1.0 — Setup iniziale
- Struttura progetto e Docker Compose
- Database Abstraction Layer (TinyFlux / TimescaleDB)
- Schema TimescaleDB con retention policy 365 giorni
"""

files["DATABASE_ADAPTER.md"] = """# Database Adapter

## Struttura file
```
backend/database/
├── adapter.py             # Classe astratta DatabaseAdapter (ABC)
├── factory.py             # get_adapter(settings)
├── tinyflux_adapter.py    # Implementazione TinyFlux
├── timescale_adapter.py   # Implementazione asyncpg
└── migrations/
    ├── 001_init.sql           # Schema TimescaleDB
    └── migrate_tinyflux.py    # Migrazione con --dry-run
```

## TinyFlux

Python puro, file CSV locale, nessuna infrastruttura.
```ini
DATABASE_BACKEND=tinyflux
TINYFLUX_PATH=./data/temperature.db
```

Limite consigliato: ~500.000 punti ≈ 3 anni con 2 sensori ogni 10 min.

## TimescaleDB
```ini
DATABASE_BACKEND=timescale
POSTGRES_USER=medmon
POSTGRES_PASSWORD=password_sicura
POSTGRES_DB=medmonitor
```

Schema principale:
```sql
CREATE TABLE temperature_readings (
    id          BIGSERIAL,
    zone        VARCHAR(20)  NOT NULL,
    sensor_id   VARCHAR(50)  NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity    DECIMAL(5,2),
    battery     SMALLINT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);
SELECT create_hypertable('temperature_readings', 'timestamp');
SELECT add_retention_policy('temperature_readings', INTERVAL '365 days');
```

## Migrazione TinyFlux → TimescaleDB
```bash
python backend/database/migrations/migrate_tinyflux.py \\
  --tinyflux-path ./data/temperature.db \\
  --postgres-dsn postgresql://user:pass@localhost/medmonitor \\
  --dry-run
```

Rimuovi --dry-run per eseguire davvero.

## Confronto

| Caratteristica | TinyFlux | TimescaleDB |
|---|---|---|
| Setup | Nessuno | Docker + SQL |
| Linguaggio | Python puro | C / PostgreSQL |
| Max punti | ~500.000 | Illimitati |
| Query SQL | No | Completo |
| Backup | cp file | pg_dump |
| Adatto per | Inizio | Produzione |
"""

files["UI_DESIGN.md"] = """# UI Design

## Stack

- `dash` + `dash-bootstrap-components` (Bootstrap 5)
- `plotly` per grafici interattivi
- `dash-iconify` per icone
- `dash-ag-grid` per tabelle avanzate
```bash
pip install dash dash-bootstrap-components plotly dash-iconify dash-ag-grid
```

## Tema default: SLATE (dark)
```python
import dash_bootstrap_components as dbc
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])
```

Temi selezionabili da UI:
- SLATE — dark grigio-blu (default)
- VAPOR — dark viola
- FLATLY — light flat
- COSMO — light minimal

## Layout
```
NAVBAR  [logo] medMonitor   ● Sistema attivo   [1 allarme]
──────────────────────────────────────────────────────────────────
SIDEBAR (160px) │ CONTENUTO
                │
[▐] Dashboard   │  [4.2°C OK] [-31.4°C !!] [1 allarme] [2/2 sens]
    Storico     │
    Allarmi     │  ┌── Frigorifero ──┐  ┌── Freezer ─────────┐
    ────        │  │ OK      4.2°C  │  │ ALLARME  -31.4°C  │
    Impostazioni│  │ ████░░░░░░░░░  │  │ █░░░░░░░░░░░░░░░  │
                │  │ 0°C      30°C  │  │ -30°C        0°C  │
                │  └────────────────┘  └───────────────────┘
                │
                │  [Grafico linea 24h con bande soglia per sensore]
                │
                │  [Tabella sensori: stato, batteria, ultimo aggiornamento]
```

## Colori semantici

| Stato | Hex | Uso |
|---|---|---|
| OK | #1D9E75 | bordo card 3px, temperatura, dot sensore |
| WARNING | #BA7517 | badge, temperatura gialla |
| CRITICAL | #E24B4A | bordo card 3px, badge, linee soglia |

## Zone card

- Bordo sinistro 3px colorato per stato
- Mostra soglie **effettive del sensore** (non quelle di zona)
- Icona ★ se override=True con tooltip "Soglie individuali"
- Gauge bar 6px fill colorato

## Pagine

1. **Dashboard** — real-time, dcc.Interval 30s
2. **Storico** — DatePickerRange, grafici Plotly, export CSV
3. **Allarmi** — AG Grid con filtri, badge WARNING/CRITICAL
4. **Impostazioni** — tabs: Generale, Soglie, Sensori, Email, Database, Sistema, Demo

## Sezione Soglie (Impostazioni)

Due livelli:
1. Default di zona — RangeSlider per fridge e freezer
2. Per sensore — card con dbc.Switch toggle override + RangeSlider sincronizzato

Pattern MATCH di Dash per gestire N sensori dinamicamente.
Slider disabilitato se override=False.

## Struttura frontend
```
frontend/
├── app.py
├── layout.py          # Navbar + sidebar
├── pages/
│   ├── dashboard.py
│   ├── history.py
│   ├── alerts.py
│   └── settings.py
├── components/
│   ├── zone_card.py   # Card con gauge e badge stato
│   ├── metric_card.py
│   ├── demo_banner.py # Banner giallo demo attiva
│   └── charts.py
├── callbacks/
└── assets/custom.css
```
"""

files["CONFIGURATION.md"] = """# Configurazione del sistema

## File .env
```ini
# ── Database ─────────────────────────────────────
DATABASE_BACKEND=tinyflux          # tinyflux | timescale
TINYFLUX_PATH=./data/temperature.db
POSTGRES_USER=medmon
POSTGRES_PASSWORD=cambia_questa_password
POSTGRES_DB=medmonitor
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# ── MQTT ─────────────────────────────────────────
MQTT_HOST=mosquitto
MQTT_PORT=1883

# ── Gateway ZigBee ───────────────────────────────
ZIGBEE_GATEWAY_IP=192.168.1.100

# ── Email ────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tua@email.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
ALERT_RECIPIENTS=dest@email.com

# ── Applicazione ─────────────────────────────────
APP_NAME=medMonitor
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USE_SSL=true
APP_THEME=slate
LOG_LEVEL=INFO
POLLING_INTERVAL_MINUTES=10
ALERT_COOLDOWN_MINUTES=30
DATA_RETENTION_DAYS=365

# ── Soglie default di zona ────────────────────────
FRIDGE_TEMP_MIN=0.0
FRIDGE_TEMP_MAX=30.0
FREEZER_TEMP_MIN=-30.0
FREEZER_TEMP_MAX=0.0

# ── Demo ─────────────────────────────────────────
DEMO_MODE=false
DEMO_SPEED=10x
```

## Soglie per sensore individuale

Salvate in data/config.json, hanno priorità su .env.
```json
{
  "thresholds": {
    "defaults": {
      "fridge":  {"min": 0.0,   "max": 30.0},
      "freezer": {"min": -30.0, "max": 0.0}
    },
    "sensors": {
      "0x00158d0001234567": {
        "name": "Frigorifero sala A",
        "zone": "fridge",
        "min": 2.0, "max": 8.0,
        "override": true
      },
      "0x00158d0007654321": {
        "name": "Freezer sala B",
        "zone": "freezer",
        "min": null, "max": null,
        "override": false
      }
    }
  }
}
```

Logica di risoluzione:
- `override=True`  → usa min/max del sensore
- `override=False` → usa min/max del default di zona

## Priorità configurazione
```
1. data/config.json   (modifiche da UI — massima priorità)
2. .env               (configurazione iniziale)
3. valori default     (hardcodati in config.py)
```
"""

files["DEMO_MODE.md"] = """# Demo Mode — Dati simulati per test usabilità

## Attivazione

Da API:
```bash
curl -X POST http://localhost:8000/api/demo/start \\
  -H "Content-Type: application/json" \\
  -d '{"speed": "10x", "scenario": "full_stress"}'
```

Da UI: Impostazioni > Demo > seleziona scenario e velocità > Avvia demo

## Scenari

| Scenario | Descrizione |
|---|---|
| `normal` | Temperature stabili, nessun allarme |
| `fridge_alarm` | Frigorifero sale sopra soglia (porta aperta simulata) |
| `freezer_alarm` | Freezer scende sotto soglia (guasto termostato) |
| `power_loss` | Entrambe le zone salgono per 2 ore (interruzione corrente) |
| `sensor_battery_low` | Batteria scende a 0, sensore va offline |
| `full_stress` | Tutti gli scenari in sequenza — demo completa |

Consigliato per primo test: `scenario=full_stress, speed=10x`
Simula 24 ore in circa 2 minuti, include allarmi e anomalie.

## Velocità simulazione

| Speed | 10 min reali simulati in |
|---|---|
| 1x | 10 minuti |
| 10x | 1 minuto |
| 60x | 10 secondi |
| 600x | 1 secondo (stress test) |

## Modello fisico generatore
```
next_temp = current
          + (base - current) * 0.05   ← mean reversion verso la base
          + gauss(0, 0.15)            ← rumore gaussiano naturale
          + scenario_drift            ← evento controllato dallo scenario
```

## Identificazione dati demo

I dati demo hanno sensor_id che inizia con `0xDEMO`.
Si cancellano con `POST /api/demo/reset` senza toccare i dati reali.

## Banner UI

Quando demo è attiva appare un banner giallo in cima a tutte le pagine:
"MODALITÀ DEMO — Scenario: X — Velocità: Yx" con pulsante "Ferma demo".

## Endpoint API demo
```
POST /api/demo/start   params: scenario, speed
POST /api/demo/stop
GET  /api/demo/status  → active, scenario, speed, step, temps correnti
POST /api/demo/reset   → cancella tutti i dati 0xDEMO*
```
"""

files["CLAUDE_SKILLS.md"] = """# Claude Skills — medMonitor

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
Cooldown configurabile. Template Jinja2 HTML. aiosmtplib asincrono.

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
"""

files["CLAUDE_PROMPTS.md"] = """# Claude Prompts — medMonitor

Usa `claude-opus-4-6` per tutti i prompt.

## Prompt 0 — Setup GitHub
```
Configura il repository GitHub per medMonitor.
1. gh repo create medMonitor --private --description "Sistema monitoraggio temperatura ZigBee"
2. git init, .gitignore (escludi .env, data/, postgres_data/, __pycache__, *.pyc)
3. .env.example completo con tutti i parametri
4. Label: backend, frontend, database, mqtt, alert, docker, ui, config, demo
5. 11 issue GitHub per le fasi di sviluppo
6. Primo commit e push su main
```

## Prompt 1 — Struttura progetto e Docker
```
Crea la struttura iniziale del progetto medMonitor.
Cartelle: backend/ frontend/ data/ docker/
Docker Compose: mosquitto, backend, frontend, postgres (profile: timescale)
Volume ./data:/app/data per TinyFlux e config.json
Dockerfile backend Python 3.11-slim
.env.example completo
```

## Prompt 2 — Database Abstraction Layer
```
Crea il Database Abstraction Layer per medMonitor.
File in backend/database/:
- adapter.py: classe astratta DatabaseAdapter (ABC)
  metodi: write_reading, get_readings, get_latest, write_alert, get_alerts, delete_demo_data
- tinyflux_adapter.py: implementazione TinyFlux
- timescale_adapter.py: implementazione asyncpg con time_bucket()
- factory.py: get_adapter(settings) legge DATABASE_BACKEND
- migrations/001_init.sql: schema TimescaleDB completo + retention 365gg
- migrations/migrate_tinyflux.py: script migrazione con --dry-run
```

## Prompt 3 — Config Service
```
Crea il sistema di configurazione per medMonitor.
- backend/models/config_model.py: Pydantic model ConfigSchema completo
  incluso ThresholdsConfig con defaults (zona) e sensors (override per sensore)
  metodo resolve(sensor_id) -> (effective_min, effective_max)
- backend/services/config_service.py: lettura gerarchica default→.env→config.json
  hot reload soglie, switch database con migrazione opzionale
- backend/routers/config.py: GET/PATCH /api/config, POST /api/config/test-email,
  POST /api/config/switch-database
- backend/routers/thresholds.py:
  GET /api/thresholds (con effective_min/max calcolati)
  PATCH /api/thresholds/defaults
  PATCH /api/thresholds/sensor/{sensor_id}
  DELETE /api/thresholds/sensor/{sensor_id}
```

## Prompt 4 — MQTT Client e API REST
```
Crea MQTT client e router FastAPI per medMonitor.
- backend/services/mqtt_client.py:
  Paho-MQTT, subscribe zigbee2mqtt/#
  Reconnect esponenziale (1s→2s→4s→max 60s)
  Parsing JSON, scrittura via DatabaseAdapter
- backend/routers/readings.py: GET /api/readings, GET /api/readings/latest
- backend/routers/sensors.py: GET /api/sensors, PUT /api/sensors/{id}
- backend/routers/alerts.py: GET /api/alerts, POST /api/alerts/test
Tutti i router usano DatabaseAdapter via Depends(). Validazione Pydantic v2.
```

## Prompt 5 — Alert Service
```
Crea il sistema di alerting per medMonitor.
- backend/services/alert_service.py:
  APScheduler ogni minuto
  Usa ThresholdsConfig.resolve(sensor_id) per soglie effettive di ogni sensore
  Livelli WARNING (0-15 min) e CRITICAL (>15 min)
  Cooldown da config (default 30 min)
- backend/services/email_service.py: aiosmtplib, multi-destinatario
- backend/templates/alert_email.html: Jinja2 HTML responsivo con colori semantici
```

## Prompt 6 — Dashboard Dash real-time
```
Crea la dashboard Plotly Dash per medMonitor.
- frontend/app.py: entry point, tema dbc.themes.SLATE
- frontend/layout.py: navbar (logo, titolo, stato, badge allarmi) + sidebar (4 voci)
- frontend/pages/dashboard.py:
  4 metric cards (temp frigorifero, temp freezer, allarmi attivi, sensori online)
  2 zone cards con gauge bar, colori semantici (#1D9E75/#BA7517/#E24B4A),
    badge stato, soglie effettive del sensore, icona ★ se override=True
  Grafico linea ultime 24h con bande add_hrect per soglie per sensore
  Tabella sensori con dot colorato, batteria, ultima lettura
  dcc.Interval aggiornamento ogni 30s
- frontend/components/demo_banner.py: banner dbc.Alert giallo se demo attiva
Segui UI_DESIGN.md per tutti i dettagli visivi.
```

## Prompt 7 — Pagine Storico e Allarmi
```
Crea le pagine Storico e Allarmi per la dashboard Dash.
- frontend/pages/history.py:
  dcc.DatePickerRange per periodo
  Line chart Plotly interattivo con zoom/pan/hover
  Toggle visibilità sensori
  Bande add_hrect soglie per sensore (effective_min/max da /api/thresholds)
  Statistiche periodo (media, min, max, std)
  Export CSV con dcc.Download
- frontend/pages/alerts.py:
  dash_ag_grid con colonne: timestamp, zona, sensore, temperatura, livello, durata
  Badge colorati WARNING/CRITICAL
  Filtri per zona e periodo
  Contatore allarmi attivi in navbar
```

## Prompt 8 — Pannello Configurazione
```
Crea il pannello Impostazioni completo per medMonitor.
frontend/pages/settings.py con dbc.Tabs:

Tab 1 — Generale: nome impianto, lingua, tema UI (toggle SLATE/FLATLY/VAPOR/COSMO)
Tab 2 — Soglie temperatura:
  Sezione "Default di zona": RangeSlider per fridge e freezer
  Sezione "Per sensore": una card per ogni sensore con:
    dbc.Switch toggle override (disabilita/abilita soglie individuali)
    dcc.RangeSlider + dbc.Input min/max sincronizzati via MATCH callback
    Pre-popolato con default zona al primo toggle ON
    Pulsante "Ripristina default zona" (disabilitato se override=False)
Tab 3 — Sensori: AG Grid modificabile (nome, zona, attivo), pairing guidato
Tab 4 — Email: form SMTP/SendGrid, multi-tag destinatari, pulsante test, badge stato
Tab 5 — Database: toggle TinyFlux/TimescaleDB, barra capacità TinyFlux,
  pulsante "Migra dati" con progress bar
Tab 6 — Sistema: slider intervalli, retention, backup, export/import config
Tab 7 — Demo: dropdown scenario (6 opzioni), dropdown velocità,
  pulsanti "Avvia demo" e "Reset dati demo"

Ogni modifica chiama PATCH /api/config o PATCH /api/thresholds
e mostra dbc.Toast di conferma.
```

## Prompt 9 — Demo Mode
```
Implementa la modalità demo per medMonitor.
- backend/services/demo_generator.py:
  Classe DemoGenerator con modello fisico:
    next_temp = current + (base-current)*0.05 + gauss(0,0.15) + scenario_drift
  6 scenari: normal, fridge_alarm, freezer_alarm, power_loss,
    sensor_battery_low, full_stress
  Loop asincrono asyncio.create_task con speed_multiplier
  sensor_id sempre prefisso "0xDEMO" per identificazione
- backend/routers/demo.py:
  POST /api/demo/start, POST /api/demo/stop
  GET /api/demo/status, POST /api/demo/reset
- frontend/components/demo_banner.py:
  dbc.Alert giallo con scenario attivo e pulsante "Ferma demo"
  Visibile in tutte le pagine quando demo è attiva
```

## Prompt 10 — Test suite completa
```
Crea la suite di test per medMonitor.
backend/tests/:
- conftest.py: fixture TinyFluxAdapter in-memory, mock MQTT, mock SMTP
- test_database_adapter.py: testa entrambi gli adapter con la stessa interfaccia
- test_api.py: testa tutti gli endpoint FastAPI con httpx AsyncClient
- test_alert_service.py: testa logica WARNING/CRITICAL e cooldown
- test_config_service.py: testa priorità config e hot reload
- test_thresholds.py: testa resolve() con override=True/False,
  che alert_service usa soglie del sensore non della zona
- test_demo_generator.py: testa che fridge_alarm supera 30°C entro 200 step,
  che sensor_id inizia con 0xDEMO
- test_migrate.py: testa script migrazione TinyFlux→TimescaleDB

Target: pytest backend/tests/ -v --cov=backend (coverage > 80%)
```
"""

files["CLAUDE_WORKFLOW.md"] = """# Claude Code Workflow — medMonitor

## Modello AI

**Usa sempre `claude-opus-4-6` per tutte le fasi del progetto.**
```bash
claude config set model claude-opus-4-6
```

## Repository GitHub
```bash
# Installa e autentica gh
sudo apt install -y gh && gh auth login

# Crea repository
gh repo create medMonitor \\
  --private \\
  --description "Sistema monitoraggio temperatura ZigBee con FastAPI, TinyFlux/TimescaleDB e Plotly Dash"

# Inizializza e primo push
git init
git add .
git commit -m "[init] struttura iniziale progetto"
git push -u origin main

# Proteggi branch main
gh api repos/{owner}/medMonitor/branches/main/protection \\
  --method PUT \\
  --field required_pull_request_reviews='{"required_approving_review_count":1}'
```

## Flusso per ogni feature
```bash
git checkout -b feature/nome-feature
# ... sviluppo con Claude Code ...
git add .
git commit -m "[feat] descrizione modifica"
git push origin feature/nome-feature
gh pr create --title "Titolo PR" --base main --label "label"
gh issue close N
```

## Tabella fasi

| Fase | Branch | Release |
|---|---|---|
| Setup + Docker | feature/project-setup | — |
| Database Adapter | feature/database-adapter | — |
| Config + Thresholds | feature/config-system | — |
| MQTT + API REST | feature/backend | v0.2.0 |
| Alert Service | feature/alerts | — |
| Dashboard real-time | feature/dashboard | v0.3.0 |
| Demo Mode | feature/demo-mode | v0.4.0 |
| Soglie per sensore | feature/per-sensor-thresholds | v0.5.0 |
| Test suite | feature/test-suite | v1.0.0 |

## Convenzioni commit
```
[feat]     nuova funzionalità
[fix]      correzione bug
[docs]     documentazione
[test]     test
[refactor] refactoring senza nuove feature
```

## Checklist pre-deploy

- [ ] .env configurato (mai committato, in .gitignore)
- [ ] .env.example committato con valori placeholder
- [ ] Password database modificata
- [ ] SMTP testato con POST /api/alerts/test
- [ ] IP gateway ZigBee corretto
- [ ] Test suite: pytest backend/tests/ -v --cov=backend (> 80%)
- [ ] docker-compose up -d — tutti i container UP
- [ ] Dashboard: http://localhost:8050
- [ ] Demo mode: scenario=full_stress, speed=10x funzionante
- [ ] Soglie per sensore salvate correttamente in data/config.json
- [ ] gh release create v1.0.0
"""

# Crea tutti i file
created = []
for filename, content in files.items():
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content.strip())
    created.append(filename)
    print(f"✓ {filename}")

print(f"\n{len(created)} file creati nella cartella corrente.")#!/usr/bin/env python3
"""
Esegui nella cartella del progetto:
  python create_docs.py
"""
import os

files = {}

files["README.md"] = """# medMonitor

Sistema di monitoraggio temperatura per celle frigorifere e freezer,
con dashboard web professionale e notifiche email automatiche.

## Caratteristiche principali

- Acquisizione dati da sensori ZigBee tramite gateway Wi-Fi/Ethernet
- Logging ogni 10 minuti (TinyFlux o PostgreSQL + TimescaleDB)
- Dashboard Plotly Dash professionale (tema dark/light)
- Soglie configurabili individualmente per ogni sensore
- Sistema di allarme email WARNING / CRITICAL
- Modalità demo con 6 scenari simulati realistici
- Deploy locale con Docker Compose

## Stack tecnologico

| Layer | Tecnologia |
|---|---|
| Backend | Python 3.11, FastAPI, APScheduler, Paho-MQTT |
| Database | TinyFlux (default) → TimescaleDB (scalabile) |
| Frontend | Plotly Dash + Dash Bootstrap Components |
| Hardware | Gateway ZigBee Wi-Fi (Sonoff ZBBridge Pro) |
| Email | SMTP (invio) + IMAP (ricezione/conferme) |
| Deploy | Windows nativo / Docker Compose |

## Avvio rapido
```bash
gh repo clone greeneye71/medMonitor
cd medMonitor
cp .env.example .env
# Modifica .env con le tue impostazioni
docker-compose up -d
```

Dashboard: http://localhost:8050
API docs:  http://localhost:8000/docs

## Modello AI

Sviluppato con **claude-opus-4-6** tramite Claude Code.
"""

files["ARCHITECTURE.md"] = """# Architettura del sistema

## Principio chiave: Database Abstraction Layer

Due database intercambiabili senza modificare il codice applicativo:
- **TinyFlux** — Python puro, zero infrastruttura, default iniziale
- **TimescaleDB** — PostgreSQL esteso, produzione, alta scalabilità

## Schema generale
```
[Sensori ZigBee]
      | ZigBee 2.4GHz
      v
[Gateway Wi-Fi/Ethernet]   Sonoff ZBBridge Pro / SLZB-06
      | MQTT TCP/IP LAN
      v
[Mosquitto MQTT Broker]    Docker
      | subscribe zigbee2mqtt/#
      v
[Backend FastAPI]
      |              |
      |              | APScheduler ogni minuto
      |              v
      |         [Alert Engine] --> SMTP/SendGrid --> Email
      |
      | DatabaseAdapter (astratto)
      |_________________________
      |                         |
      v                         v
[TinyFlux]               [TimescaleDB]
file CSV locale           PostgreSQL+estensione
      |
      v
[Frontend Plotly Dash]    http://localhost:8050
```

## Database Abstraction Layer
```python
class DatabaseAdapter(ABC):
    async def write_reading(self, reading): ...
    async def get_readings(self, zone, from_dt, to_dt, limit): ...
    async def get_latest(self): ...
    async def write_alert(self, alert): ...
    async def get_alerts(self, limit): ...
    async def delete_demo_data(self): ...

# Factory: legge DATABASE_BACKEND da config
def get_adapter(settings) -> DatabaseAdapter:
    if settings.database_backend == "tinyflux":
        return TinyFluxAdapter(settings.tinyflux_path)
    return TimescaleAdapter(settings.postgres_dsn)
```

## Quando migrare a TimescaleDB

| Condizione | Azione |
|---|---|
| > 10 sensori attivi | Valutare migrazione |
| File TinyFlux > 500 MB | Pianificare migrazione |
| Query lente (> 2s) | Migrare |
| > 3 anni di dati | Migrare |

## Porte di rete

| Servizio | Porta |
|---|---|
| Dash frontend | 8050 |
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Mosquitto MQTT | 1883 |

## Stadi di scalabilità

- **Stadio 1**: TinyFlux, 2-5 sensori, 1 sede, Docker locale
- **Stadio 2**: TimescaleDB, 10-50 sensori, 1-3 sedi, VPS
- **Stadio 3**: InfluxDB/QuestDB, 100+ sensori, multi-sede, cloud
"""

files["HARDWARE.md"] = """# Hardware consigliato

## Gateway ZigBee

Poiché l'app gira su VM, si usa un gateway con connettività
Wi-Fi o Ethernet invece di un dongle USB.

### Sonoff ZBBridge Pro (consigliato) ~22 €
- Wi-Fi 2.4GHz, firmware nativo o Tasmota
- MQTT nativo, ZigBee 3.0, chip EFR32MG21

### SLZB-06 ~35 € (Ethernet, più stabile)
- Ethernet, open source, compatibile Zigbee2MQTT

## Sensori temperatura

### Frigorifero (0°C / +30°C)
- Sonoff SNZB-02D: ~14 €, -20/+60°C, ±0.5°C, display LCD
- MOES ZSS-ZK-THL: ~12 €, -10/+50°C, ±0.3°C

### Freezer (-30°C / 0°C)
- Aqara Temperature T1: ~16 €, -40/+85°C, ±0.3°C  ← consigliato
- Sonoff SNZB-02P: ~12 €, -40/+85°C, IP65

## Costo totale configurazione base

| Componente | Costo |
|---|---|
| Gateway Sonoff ZBBridge Pro | ~22 € |
| Sensore frigorifero (SNZB-02D) | ~14 € |
| Sensore freezer (Aqara T1) | ~16 € |
| **Totale** | **~52 €** |

## Requisiti VM

| Risorsa | Minimo | Consigliato |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Disco | 20 GB | 50 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
"""

files["INSTALLATION.md"] = """# Guida all'installazione

## 1. Prerequisiti
```bash
# Docker
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker

# GitHub CLI
sudo apt install -y gh
gh auth login
```

## 2. Clone e configurazione
```bash
gh repo clone greeneye71/medMonitor
cd medMonitor
cp .env.example .env
nano .env
```

Parametri minimi in .env:
```ini
DATABASE_BACKEND=tinyflux
TINYFLUX_PATH=./data/temperature.db
MQTT_HOST=mosquitto
ZIGBEE_GATEWAY_IP=192.168.1.100
SMTP_HOST=smtp.gmail.com
SMTP_USER=tua@email.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
ALERT_RECIPIENTS=destinatario@email.com
FRIDGE_TEMP_MIN=0.0
FRIDGE_TEMP_MAX=30.0
FREEZER_TEMP_MIN=-30.0
FREEZER_TEMP_MAX=0.0
```

## 3. Avvio
```bash
docker-compose up -d
docker-compose ps
```

## 4. Verifica

- Dashboard: http://localhost:8050
- API docs:   http://localhost:8000/docs

## 5. Test con modalità demo
```bash
curl -X POST http://localhost:8000/api/demo/start \\
  -H "Content-Type: application/json" \\
  -d '{"speed": "10x", "scenario": "full_stress"}'
```

Apri http://localhost:8050 — vedrai il banner demo giallo.

## 6. Backup
```bash
# TinyFlux
cp data/temperature.db backup_$(date +%Y%m%d).db

# TimescaleDB
docker-compose exec postgres pg_dump -U medmon medmonitor > backup_$(date +%Y%m%d).sql
```
"""

files["ALERTS.md"] = """# Configurazione allarmi e notifiche

## Soglie di temperatura

Ogni sensore ha soglie proprie. I nuovi sensori ereditano il default di zona.

| Zona | Min default | Max default |
|---|---|---|
| Frigorifero | 0°C | +30°C |
| Freezer | -30°C | 0°C |

> Modifica le soglie per sensore: Impostazioni > Soglie temperatura

## Livelli di allarme

| Livello | Condizione | Azione |
|---|---|---|
| WARNING | Fuori soglia 0-15 min | Email con oggetto [AVVISO] |
| CRITICAL | Fuori soglia > 15 min | Email ogni 30 min con oggetto [ALLARME CRITICO] |

## Configurazione email

### Gmail (App Password)
1. Account Google > Sicurezza > Password per le app
2. In .env:
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tuo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_RECIPIENTS=dest1@email.com,dest2@email.com
```

### SendGrid
```ini
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxxxxxxxxxxxxx
```

## Test email
```bash
curl -X POST http://localhost:8000/api/alerts/test \\
  -H "Content-Type: application/json" \\
  -d '{"email": "tuo@email.com"}'
```

## Cooldown

Default: 30 minuti tra email successive per la stessa zona.
Modificabile in .env: `ALERT_COOLDOWN_MINUTES=30`
"""

files["API.md"] = """# Documentazione API REST

Base URL: `http://localhost:8000/api`
Swagger UI: `http://localhost:8000/docs`

## Readings

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /readings | Letture con filtri (zone, from, to, limit) |
| GET | /readings/latest | Ultima lettura per ogni zona |

## Alerts

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /alerts | Storico allarmi |
| POST | /alerts/test | Invia email di test |

## Sensors

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /sensors | Lista sensori registrati |
| PUT | /sensors/{id} | Aggiorna nome/zona sensore |

## Thresholds (soglie per sensore)

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /thresholds | Defaults zona + soglie per sensore con effective_min/max |
| PATCH | /thresholds/defaults | Aggiorna default di zona |
| PATCH | /thresholds/sensor/{sensor_id} | Soglie individuali sensore |
| DELETE | /thresholds/sensor/{sensor_id} | Ripristina default zona |

Esempio PATCH soglie sensore:
```json
{ "min": -22.0, "max": -16.0, "override": true }
```

## Config

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /config | Configurazione completa |
| PATCH | /config | Aggiorna parametri runtime |
| POST | /config/test-email | Test SMTP |
| POST | /config/switch-database | Cambia backend DB |

## Demo

| Metodo | Endpoint | Descrizione |
|---|---|---|
| POST | /demo/start | Avvia demo (scenario, speed) |
| POST | /demo/stop | Ferma demo |
| GET | /demo/status | Stato corrente |
| POST | /demo/reset | Cancella dati demo |
"""

files["CHANGELOG.md"] = """# Changelog

## v0.5.0 — Soglie per sensore individuale
- Soglie min/max configurabili per ogni sensore separatamente
- Override attivabile singolarmente, eredita default zona se disattivato
- Indicatore ★ in dashboard per sensori con soglie personalizzate
- Bande soglia individuali nel grafico storico

## v0.4.0 — Demo mode
- 6 scenari: normal, fridge_alarm, freezer_alarm, power_loss,
  sensor_battery_low, full_stress
- Generatore fisico: mean reversion + rumore gaussiano + drift scenario
- Velocità configurabile: 1x / 10x / 60x / 600x
- Banner demo in UI, reset dati con un click

## v0.3.0 — Frontend completo
- Dashboard Plotly Dash con tema SLATE dark
- Pagine: Dashboard, Storico, Allarmi, Impostazioni
- Pannello configurazione completo con tabs

## v0.2.0 — Backend completo
- MQTT client con reconnect esponenziale automatico
- API REST FastAPI con tutti gli endpoint
- Alert service WARNING/CRITICAL con cooldown

## v0.1.0 — Setup iniziale
- Struttura progetto e Docker Compose
- Database Abstraction Layer (TinyFlux / TimescaleDB)
- Schema TimescaleDB con retention policy 365 giorni
"""

files["DATABASE_ADAPTER.md"] = """# Database Adapter

## Struttura file
```
backend/database/
├── adapter.py             # Classe astratta DatabaseAdapter (ABC)
├── factory.py             # get_adapter(settings)
├── tinyflux_adapter.py    # Implementazione TinyFlux
├── timescale_adapter.py   # Implementazione asyncpg
└── migrations/
    ├── 001_init.sql           # Schema TimescaleDB
    └── migrate_tinyflux.py    # Migrazione con --dry-run
```

## TinyFlux

Python puro, file CSV locale, nessuna infrastruttura.
```ini
DATABASE_BACKEND=tinyflux
TINYFLUX_PATH=./data/temperature.db
```

Limite consigliato: ~500.000 punti ≈ 3 anni con 2 sensori ogni 10 min.

## TimescaleDB
```ini
DATABASE_BACKEND=timescale
POSTGRES_USER=medmon
POSTGRES_PASSWORD=password_sicura
POSTGRES_DB=medmonitor
```

Schema principale:
```sql
CREATE TABLE temperature_readings (
    id          BIGSERIAL,
    zone        VARCHAR(20)  NOT NULL,
    sensor_id   VARCHAR(50)  NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity    DECIMAL(5,2),
    battery     SMALLINT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);
SELECT create_hypertable('temperature_readings', 'timestamp');
SELECT add_retention_policy('temperature_readings', INTERVAL '365 days');
```

## Migrazione TinyFlux → TimescaleDB
```bash
python backend/database/migrations/migrate_tinyflux.py \\
  --tinyflux-path ./data/temperature.db \\
  --postgres-dsn postgresql://user:pass@localhost/medmonitor \\
  --dry-run
```

Rimuovi --dry-run per eseguire davvero.

## Confronto

| Caratteristica | TinyFlux | TimescaleDB |
|---|---|---|
| Setup | Nessuno | Docker + SQL |
| Linguaggio | Python puro | C / PostgreSQL |
| Max punti | ~500.000 | Illimitati |
| Query SQL | No | Completo |
| Backup | cp file | pg_dump |
| Adatto per | Inizio | Produzione |
"""

files["UI_DESIGN.md"] = """# UI Design

## Stack

- `dash` + `dash-bootstrap-components` (Bootstrap 5)
- `plotly` per grafici interattivi
- `dash-iconify` per icone
- `dash-ag-grid` per tabelle avanzate
```bash
pip install dash dash-bootstrap-components plotly dash-iconify dash-ag-grid
```

## Tema default: SLATE (dark)
```python
import dash_bootstrap_components as dbc
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE])
```

Temi selezionabili da UI:
- SLATE — dark grigio-blu (default)
- VAPOR — dark viola
- FLATLY — light flat
- COSMO — light minimal

## Layout
```
NAVBAR  [logo] medMonitor   ● Sistema attivo   [1 allarme]
──────────────────────────────────────────────────────────────────
SIDEBAR (160px) │ CONTENUTO
                │
[▐] Dashboard   │  [4.2°C OK] [-31.4°C !!] [1 allarme] [2/2 sens]
    Storico     │
    Allarmi     │  ┌── Frigorifero ──┐  ┌── Freezer ─────────┐
    ────        │  │ OK      4.2°C  │  │ ALLARME  -31.4°C  │
    Impostazioni│  │ ████░░░░░░░░░  │  │ █░░░░░░░░░░░░░░░  │
                │  │ 0°C      30°C  │  │ -30°C        0°C  │
                │  └────────────────┘  └───────────────────┘
                │
                │  [Grafico linea 24h con bande soglia per sensore]
                │
                │  [Tabella sensori: stato, batteria, ultimo aggiornamento]
```

## Colori semantici

| Stato | Hex | Uso |
|---|---|---|
| OK | #1D9E75 | bordo card 3px, temperatura, dot sensore |
| WARNING | #BA7517 | badge, temperatura gialla |
| CRITICAL | #E24B4A | bordo card 3px, badge, linee soglia |

## Zone card

- Bordo sinistro 3px colorato per stato
- Mostra soglie **effettive del sensore** (non quelle di zona)
- Icona ★ se override=True con tooltip "Soglie individuali"
- Gauge bar 6px fill colorato

## Pagine

1. **Dashboard** — real-time, dcc.Interval 30s
2. **Storico** — DatePickerRange, grafici Plotly, export CSV
3. **Allarmi** — AG Grid con filtri, badge WARNING/CRITICAL
4. **Impostazioni** — tabs: Generale, Soglie, Sensori, Email, Database, Sistema, Demo

## Sezione Soglie (Impostazioni)

Due livelli:
1. Default di zona — RangeSlider per fridge e freezer
2. Per sensore — card con dbc.Switch toggle override + RangeSlider sincronizzato

Pattern MATCH di Dash per gestire N sensori dinamicamente.
Slider disabilitato se override=False.

## Struttura frontend
```
frontend/
├── app.py
├── layout.py          # Navbar + sidebar
├── pages/
│   ├── dashboard.py
│   ├── history.py
│   ├── alerts.py
│   └── settings.py
├── components/
│   ├── zone_card.py   # Card con gauge e badge stato
│   ├── metric_card.py
│   ├── demo_banner.py # Banner giallo demo attiva
│   └── charts.py
├── callbacks/
└── assets/custom.css
```
"""

files["CONFIGURATION.md"] = """# Configurazione del sistema

## File .env
```ini
# ── Database ─────────────────────────────────────
DATABASE_BACKEND=tinyflux          # tinyflux | timescale
TINYFLUX_PATH=./data/temperature.db
POSTGRES_USER=medmon
POSTGRES_PASSWORD=cambia_questa_password
POSTGRES_DB=medmonitor
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# ── MQTT ─────────────────────────────────────────
MQTT_HOST=mosquitto
MQTT_PORT=1883

# ── Gateway ZigBee ───────────────────────────────
ZIGBEE_GATEWAY_IP=192.168.1.100

# ── Email ────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tua@email.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
ALERT_RECIPIENTS=dest@email.com

# ── Applicazione ─────────────────────────────────
APP_NAME=medMonitor
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USE_SSL=true
APP_THEME=slate
LOG_LEVEL=INFO
POLLING_INTERVAL_MINUTES=10
ALERT_COOLDOWN_MINUTES=30
DATA_RETENTION_DAYS=365

# ── Soglie default di zona ────────────────────────
FRIDGE_TEMP_MIN=0.0
FRIDGE_TEMP_MAX=30.0
FREEZER_TEMP_MIN=-30.0
FREEZER_TEMP_MAX=0.0

# ── Demo ─────────────────────────────────────────
DEMO_MODE=false
DEMO_SPEED=10x
```

## Soglie per sensore individuale

Salvate in data/config.json, hanno priorità su .env.
```json
{
  "thresholds": {
    "defaults": {
      "fridge":  {"min": 0.0,   "max": 30.0},
      "freezer": {"min": -30.0, "max": 0.0}
    },
    "sensors": {
      "0x00158d0001234567": {
        "name": "Frigorifero sala A",
        "zone": "fridge",
        "min": 2.0, "max": 8.0,
        "override": true
      },
      "0x00158d0007654321": {
        "name": "Freezer sala B",
        "zone": "freezer",
        "min": null, "max": null,
        "override": false
      }
    }
  }
}
```

Logica di risoluzione:
- `override=True`  → usa min/max del sensore
- `override=False` → usa min/max del default di zona

## Priorità configurazione
```
1. data/config.json   (modifiche da UI — massima priorità)
2. .env               (configurazione iniziale)
3. valori default     (hardcodati in config.py)
```
"""

files["DEMO_MODE.md"] = """# Demo Mode — Dati simulati per test usabilità

## Attivazione

Da API:
```bash
curl -X POST http://localhost:8000/api/demo/start \\
  -H "Content-Type: application/json" \\
  -d '{"speed": "10x", "scenario": "full_stress"}'
```

Da UI: Impostazioni > Demo > seleziona scenario e velocità > Avvia demo

## Scenari

| Scenario | Descrizione |
|---|---|
| `normal` | Temperature stabili, nessun allarme |
| `fridge_alarm` | Frigorifero sale sopra soglia (porta aperta simulata) |
| `freezer_alarm` | Freezer scende sotto soglia (guasto termostato) |
| `power_loss` | Entrambe le zone salgono per 2 ore (interruzione corrente) |
| `sensor_battery_low` | Batteria scende a 0, sensore va offline |
| `full_stress` | Tutti gli scenari in sequenza — demo completa |

Consigliato per primo test: `scenario=full_stress, speed=10x`
Simula 24 ore in circa 2 minuti, include allarmi e anomalie.

## Velocità simulazione

| Speed | 10 min reali simulati in |
|---|---|
| 1x | 10 minuti |
| 10x | 1 minuto |
| 60x | 10 secondi |
| 600x | 1 secondo (stress test) |

## Modello fisico generatore
```
next_temp = current
          + (base - current) * 0.05   ← mean reversion verso la base
          + gauss(0, 0.15)            ← rumore gaussiano naturale
          + scenario_drift            ← evento controllato dallo scenario
```

## Identificazione dati demo

I dati demo hanno sensor_id che inizia con `0xDEMO`.
Si cancellano con `POST /api/demo/reset` senza toccare i dati reali.

## Banner UI

Quando demo è attiva appare un banner giallo in cima a tutte le pagine:
"MODALITÀ DEMO — Scenario: X — Velocità: Yx" con pulsante "Ferma demo".

## Endpoint API demo
```
POST /api/demo/start   params: scenario, speed
POST /api/demo/stop
GET  /api/demo/status  → active, scenario, speed, step, temps correnti
POST /api/demo/reset   → cancella tutti i dati 0xDEMO*
```
"""

files["CLAUDE_SKILLS.md"] = """# Claude Skills — medMonitor

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
Cooldown configurabile. Template Jinja2 HTML. aiosmtplib asincrono.

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
"""

files["CLAUDE_PROMPTS.md"] = """# Claude Prompts — medMonitor

Usa `claude-opus-4-6` per tutti i prompt.

## Prompt 0 — Setup GitHub
```
Configura il repository GitHub per medMonitor.
1. gh repo create medMonitor --private --description "Sistema monitoraggio temperatura ZigBee"
2. git init, .gitignore (escludi .env, data/, postgres_data/, __pycache__, *.pyc)
3. .env.example completo con tutti i parametri
4. Label: backend, frontend, database, mqtt, alert, docker, ui, config, demo
5. 11 issue GitHub per le fasi di sviluppo
6. Primo commit e push su main
```

## Prompt 1 — Struttura progetto e Docker
```
Crea la struttura iniziale del progetto medMonitor.
Cartelle: backend/ frontend/ data/ docker/
Docker Compose: mosquitto, backend, frontend, postgres (profile: timescale)
Volume ./data:/app/data per TinyFlux e config.json
Dockerfile backend Python 3.11-slim
.env.example completo
```

## Prompt 2 — Database Abstraction Layer
```
Crea il Database Abstraction Layer per medMonitor.
File in backend/database/:
- adapter.py: classe astratta DatabaseAdapter (ABC)
  metodi: write_reading, get_readings, get_latest, write_alert, get_alerts, delete_demo_data
- tinyflux_adapter.py: implementazione TinyFlux
- timescale_adapter.py: implementazione asyncpg con time_bucket()
- factory.py: get_adapter(settings) legge DATABASE_BACKEND
- migrations/001_init.sql: schema TimescaleDB completo + retention 365gg
- migrations/migrate_tinyflux.py: script migrazione con --dry-run
```

## Prompt 3 — Config Service
```
Crea il sistema di configurazione per medMonitor.
- backend/models/config_model.py: Pydantic model ConfigSchema completo
  incluso ThresholdsConfig con defaults (zona) e sensors (override per sensore)
  metodo resolve(sensor_id) -> (effective_min, effective_max)
- backend/services/config_service.py: lettura gerarchica default→.env→config.json
  hot reload soglie, switch database con migrazione opzionale
- backend/routers/config.py: GET/PATCH /api/config, POST /api/config/test-email,
  POST /api/config/switch-database
- backend/routers/thresholds.py:
  GET /api/thresholds (con effective_min/max calcolati)
  PATCH /api/thresholds/defaults
  PATCH /api/thresholds/sensor/{sensor_id}
  DELETE /api/thresholds/sensor/{sensor_id}
```

## Prompt 4 — MQTT Client e API REST
```
Crea MQTT client e router FastAPI per medMonitor.
- backend/services/mqtt_client.py:
  Paho-MQTT, subscribe zigbee2mqtt/#
  Reconnect esponenziale (1s→2s→4s→max 60s)
  Parsing JSON, scrittura via DatabaseAdapter
- backend/routers/readings.py: GET /api/readings, GET /api/readings/latest
- backend/routers/sensors.py: GET /api/sensors, PUT /api/sensors/{id}
- backend/routers/alerts.py: GET /api/alerts, POST /api/alerts/test
Tutti i router usano DatabaseAdapter via Depends(). Validazione Pydantic v2.
```

## Prompt 5 — Alert Service
```
Crea il sistema di alerting per medMonitor.
- backend/services/alert_service.py:
  APScheduler ogni minuto
  Usa ThresholdsConfig.resolve(sensor_id) per soglie effettive di ogni sensore
  Livelli WARNING (0-15 min) e CRITICAL (>15 min)
  Cooldown da config (default 30 min)
- backend/services/email_service.py: aiosmtplib, multi-destinatario
- backend/templates/alert_email.html: Jinja2 HTML responsivo con colori semantici
```

## Prompt 6 — Dashboard Dash real-time
```
Crea la dashboard Plotly Dash per medMonitor.
- frontend/app.py: entry point, tema dbc.themes.SLATE
- frontend/layout.py: navbar (logo, titolo, stato, badge allarmi) + sidebar (4 voci)
- frontend/pages/dashboard.py:
  4 metric cards (temp frigorifero, temp freezer, allarmi attivi, sensori online)
  2 zone cards con gauge bar, colori semantici (#1D9E75/#BA7517/#E24B4A),
    badge stato, soglie effettive del sensore, icona ★ se override=True
  Grafico linea ultime 24h con bande add_hrect per soglie per sensore
  Tabella sensori con dot colorato, batteria, ultima lettura
  dcc.Interval aggiornamento ogni 30s
- frontend/components/demo_banner.py: banner dbc.Alert giallo se demo attiva
Segui UI_DESIGN.md per tutti i dettagli visivi.
```

## Prompt 7 — Pagine Storico e Allarmi
```
Crea le pagine Storico e Allarmi per la dashboard Dash.
- frontend/pages/history.py:
  dcc.DatePickerRange per periodo
  Line chart Plotly interattivo con zoom/pan/hover
  Toggle visibilità sensori
  Bande add_hrect soglie per sensore (effective_min/max da /api/thresholds)
  Statistiche periodo (media, min, max, std)
  Export CSV con dcc.Download
- frontend/pages/alerts.py:
  dash_ag_grid con colonne: timestamp, zona, sensore, temperatura, livello, durata
  Badge colorati WARNING/CRITICAL
  Filtri per zona e periodo
  Contatore allarmi attivi in navbar
```

## Prompt 8 — Pannello Configurazione
```
Crea il pannello Impostazioni completo per medMonitor.
frontend/pages/settings.py con dbc.Tabs:

Tab 1 — Generale: nome impianto, lingua, tema UI (toggle SLATE/FLATLY/VAPOR/COSMO)
Tab 2 — Soglie temperatura:
  Sezione "Default di zona": RangeSlider per fridge e freezer
  Sezione "Per sensore": una card per ogni sensore con:
    dbc.Switch toggle override (disabilita/abilita soglie individuali)
    dcc.RangeSlider + dbc.Input min/max sincronizzati via MATCH callback
    Pre-popolato con default zona al primo toggle ON
    Pulsante "Ripristina default zona" (disabilitato se override=False)
Tab 3 — Sensori: AG Grid modificabile (nome, zona, attivo), pairing guidato
Tab 4 — Email: form SMTP/SendGrid, multi-tag destinatari, pulsante test, badge stato
Tab 5 — Database: toggle TinyFlux/TimescaleDB, barra capacità TinyFlux,
  pulsante "Migra dati" con progress bar
Tab 6 — Sistema: slider intervalli, retention, backup, export/import config
Tab 7 — Demo: dropdown scenario (6 opzioni), dropdown velocità,
  pulsanti "Avvia demo" e "Reset dati demo"

Ogni modifica chiama PATCH /api/config o PATCH /api/thresholds
e mostra dbc.Toast di conferma.
```

## Prompt 9 — Demo Mode
```
Implementa la modalità demo per medMonitor.
- backend/services/demo_generator.py:
  Classe DemoGenerator con modello fisico:
    next_temp = current + (base-current)*0.05 + gauss(0,0.15) + scenario_drift
  6 scenari: normal, fridge_alarm, freezer_alarm, power_loss,
    sensor_battery_low, full_stress
  Loop asincrono asyncio.create_task con speed_multiplier
  sensor_id sempre prefisso "0xDEMO" per identificazione
- backend/routers/demo.py:
  POST /api/demo/start, POST /api/demo/stop
  GET /api/demo/status, POST /api/demo/reset
- frontend/components/demo_banner.py:
  dbc.Alert giallo con scenario attivo e pulsante "Ferma demo"
  Visibile in tutte le pagine quando demo è attiva
```

## Prompt 10 — Test suite completa
```
Crea la suite di test per medMonitor.
backend/tests/:
- conftest.py: fixture TinyFluxAdapter in-memory, mock MQTT, mock SMTP
- test_database_adapter.py: testa entrambi gli adapter con la stessa interfaccia
- test_api.py: testa tutti gli endpoint FastAPI con httpx AsyncClient
- test_alert_service.py: testa logica WARNING/CRITICAL e cooldown
- test_config_service.py: testa priorità config e hot reload
- test_thresholds.py: testa resolve() con override=True/False,
  che alert_service usa soglie del sensore non della zona
- test_demo_generator.py: testa che fridge_alarm supera 30°C entro 200 step,
  che sensor_id inizia con 0xDEMO
- test_migrate.py: testa script migrazione TinyFlux→TimescaleDB

Target: pytest backend/tests/ -v --cov=backend (coverage > 80%)
```
"""

files["CLAUDE_WORKFLOW.md"] = """# Claude Code Workflow — medMonitor

## Modello AI

**Usa sempre `claude-opus-4-6` per tutte le fasi del progetto.**
```bash
claude config set model claude-opus-4-6
```

## Repository GitHub
```bash
# Installa e autentica gh
sudo apt install -y gh && gh auth login

# Crea repository
gh repo create medMonitor \\
  --private \\
  --description "Sistema monitoraggio temperatura ZigBee con FastAPI, TinyFlux/TimescaleDB e Plotly Dash"

# Inizializza e primo push
git init
git add .
git commit -m "[init] struttura iniziale progetto"
git push -u origin main

# Proteggi branch main
gh api repos/{owner}/medMonitor/branches/main/protection \\
  --method PUT \\
  --field required_pull_request_reviews='{"required_approving_review_count":1}'
```

## Flusso per ogni feature
```bash
git checkout -b feature/nome-feature
# ... sviluppo con Claude Code ...
git add .
git commit -m "[feat] descrizione modifica"
git push origin feature/nome-feature
gh pr create --title "Titolo PR" --base main --label "label"
gh issue close N
```

## Tabella fasi

| Fase | Branch | Release |
|---|---|---|
| Setup + Docker | feature/project-setup | — |
| Database Adapter | feature/database-adapter | — |
| Config + Thresholds | feature/config-system | — |
| MQTT + API REST | feature/backend | v0.2.0 |
| Alert Service | feature/alerts | — |
| Dashboard real-time | feature/dashboard | v0.3.0 |
| Demo Mode | feature/demo-mode | v0.4.0 |
| Soglie per sensore | feature/per-sensor-thresholds | v0.5.0 |
| Test suite | feature/test-suite | v1.0.0 |

## Convenzioni commit
```
[feat]     nuova funzionalità
[fix]      correzione bug
[docs]     documentazione
[test]     test
[refactor] refactoring senza nuove feature
```

## Checklist pre-deploy

- [ ] .env configurato (mai committato, in .gitignore)
- [ ] .env.example committato con valori placeholder
- [ ] Password database modificata
- [ ] SMTP testato con POST /api/alerts/test
- [ ] IP gateway ZigBee corretto
- [ ] Test suite: pytest backend/tests/ -v --cov=backend (> 80%)
- [ ] docker-compose up -d — tutti i container UP
- [ ] Dashboard: http://localhost:8050
- [ ] Demo mode: scenario=full_stress, speed=10x funzionante
- [ ] Soglie per sensore salvate correttamente in data/config.json
- [ ] gh release create v1.0.0
"""

# Crea tutti i file
created = []
for filename, content in files.items():
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content.strip())
    created.append(filename)
    print(f"✓ {filename}")

print(f"\n{len(created)} file creati nella cartella corrente.")