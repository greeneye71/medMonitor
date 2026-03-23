# Claude Prompts — medMonitor

Usa `claude-opus-4-6` per tutti i prompt.

## Prompt 0 — Setup GitHub
```
Configura il repository GitHub per medMonitor.
1. gh repo create medMonitor --private --description "medMonitor — monitoraggio temperatura ZigBee"
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
- backend/services/email_service.py: aiosmtplib (SMTP invio), aioimaplib (IMAP ricezione)
  SMTP: invio allarmi multi-destinatario con TLS/SSL
  IMAP: monitoraggio risposte operatore (ACK, MUTE, ESCALATE, STATUS)
- backend/services/imap_service.py: polling IMAP per conferme e comandi via email
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
Tab 4 — Email: form SMTP (invio) e IMAP (ricezione), multi-tag destinatari, pulsante test SMTP e IMAP, badge stato
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