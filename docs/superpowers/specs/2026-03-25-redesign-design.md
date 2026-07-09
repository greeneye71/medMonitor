# medMonitor v2 — Redesign UI + Robustezza

**Data:** 2026-03-25
**Branch:** feature/ui-redesign-v2
**Versione:** 2.0.0

---

## 1. Obiettivi

1. Sostituire l'interfaccia attuale (Dash SLATE dark, sidebar larga, metric cards generiche) con un design **Modern SaaS Light** coerente e professionale.
2. Aggiungere visibilità e controllo sullo stato dei servizi backend (MQTT, APScheduler, Database) direttamente dal frontend.
3. Rendere la configurazione sensori completamente funzionante: auto-discovery via MQTT + aggiunta manuale.
4. Aumentare la robustezza: frontend resiliente agli errori API, backend con error handling consistente, nuovi endpoint di health/control.
5. Archiviazione automatica dei dati: letture e allarmi più vecchi di 180 giorni vengono esportati in CSV e rimossi dal database per mantenerlo piccolo.

---

## 2. Design System

### Palette colori

| Ruolo | Colore | Hex |
|---|---|---|
| Background pagina | Slate 50 | `#f8fafc` |
| Card / Surface | Bianco | `#ffffff` |
| Sidebar | Slate 900 | `#0f172a` |
| Sidebar hover/active | Slate 800 | `#1e293b` |
| Testo primario | Slate 900 | `#0f172a` |
| Testo secondario | Slate 500 | `#64748b` |
| Testo muted | Slate 400 | `#94a3b8` |
| OK / Normal | Green 500 | `#22c55e` |
| WARNING | Amber 500 | `#f59e0b` |
| CRITICAL | Red 500 | `#ef4444` |
| Info / Azioni | Blue 500 | `#3b82f6` |
| Bordo | Slate 200 | `#e2e8f0` |

### Componenti base

- **Card**: `background #fff`, `border-radius 12px`, `box-shadow 0 1px 3px rgba(0,0,0,0.06)`, padding 16px
- **Badge stato**: pill colorato (OK=green-100/green-800, WARNING=amber-100/amber-800, CRITICAL=red-100/red-800)
- **Pulsante primario**: `background #0f172a`, testo bianco, border-radius 8px
- **Input**: border Slate 200, focus ring Blue 500
- **Dot di stato servizio**: cerchio 8px colorato (green=attivo, amber=degradato, red=down)

### Colori zona (per grafico multi-zona)

Ogni zona riceve automaticamente un colore base dall'array: `[#22c55e, #3b82f6, #a855f7, #f59e0b, #ec4899, #14b8a6]`. Il primo sensore della zona usa il colore pieno (stroke-width 2.5px), i successivi sfumature chiare con linea tratteggiata (8,3).

---

## 3. Layout strutturale

```
┌─────────────────────────────────────────────────────┐
│ SIDEBAR (220px, fixed, #0f172a)                     │
│  medMonitor                                          │
│  ─────────────────────                              │
│  📊 Dashboard          ← active: bg #1e293b        │
│  📅 Storico                                         │
│  🔔 Allarmi    [2]    ← badge rosso se allarmi     │
│  ⚙️  Impostazioni                                   │
│  🖥️  Sistema                                        │
│  ─────────────────────                              │
│  ● ● ●  (MQTT · SCH · DB)  ← dot stato servizi    │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ MAIN CONTENT (margin-left 220px, background #f8fafc)│
│  [Page header: titolo + timestamp + refresh btn]   │
│  [Contenuto pagina]                                 │
└─────────────────────────────────────────────────────┘
```

**Sidebar:**
- Larghezza fissa 220px (ridotta rispetto all'attuale)
- Logo/nome in alto, nav items con icona + label
- Badge numerico rosso su "Allarmi" se ci sono allarmi attivi
- In fondo: 3 dot colorati (MQTT, Scheduler, DB) con tooltip al hover
- Voce attiva: background `#1e293b`, testo bianco

**Main content:**
- Ogni pagina ha un `page-header` con: titolo H1 (font-size 20px, font-weight 700), timestamp ultimo aggiornamento, pulsante refresh manuale
- Padding 24px su tutti i lati
- Max-width 1400px, centrato

---

## 4. Pagine

### 4.1 Dashboard

**Struttura verticale:**

1. **Zone cards** — griglia dinamica costruita da `GET /api/zones` (1 card per zona, `auto-fill minmax(280px, 1fr)`). Ogni card:
   - Header: nome zona (uppercase, small) + badge stato (OK/WARNING/CRITICAL)
   - Temperatura prominente (font-size 36px, font-weight 800, colore semantico)
   - Sensori della zona: lista compatta con ultima temp + icona batteria
   - Progress bar 4px: posizione temperatura rispetto a soglie (min→max)
   - Soglie min/max ai margini della bar
   - Border-left 4px colorato per stato
   - Box-shadow intensificato se CRITICAL (red glow)

2. **Grafico 24h** — card a larghezza piena, selettore 6h/24h/7g, multi-sensore multi-zona

3. **Tabella sensori** — card a larghezza piena, compatta: ID, nome, zona (badge colorato), ultima temp, batteria (progress bar 40px), "N sec fa"

**Aggiornamento:** `dcc.Interval` 30s. Indicatore "Aggiornato alle HH:MM:SS" nel page-header.

**Resilienza:** se API non risponde, ogni card mostra stato "–" con indicatore giallo "Backend non raggiungibile" invece di crash.

### 4.2 Storico

1. **Barra filtri** (card): DatePickerRange (default: ultimi 7 giorni), Dropdown zona (multi), Dropdown sensori (multi, cascata dalla zona), Bottone "Cerca" + "Esporta CSV"
2. **Grafico** (card, height 450px): placeholder "Seleziona un periodo e clicca Cerca" se vuoto; multi-zona multi-sensore con pan/zoom abilitato
3. **Statistiche** (card): per ogni zona selezionata — Media, Min, Max, N° letture, % tempo fuori soglia

### 4.3 Allarmi

1. **Sommario** (riga): badge "X critici" (red) + badge "Y warning" (amber) + contatore "Z totali periodo"
2. **Filtri inline** (riga): Zona, Livello, DateRange — tutto su una riga, compatto
3. **AG-Grid** (card):
   - Colonne: Data/Ora, Zona (badge colorato), Sensore, Temp (°C), Livello (colored pill), Durata, Messaggio
   - Tema: `ag-theme-quartz` (light, sostituisce alpine-dark)
   - Altezza: 500px, pagination 25 righe
   - Row colorata: background `#fef2f2` se CRITICAL, `#fffbeb` se WARNING
   - Aggiornamento automatico ogni 60s

### 4.4 Impostazioni

**5 tab** (ridotti da 7, Database e log spostati in Sistema):

**Tab 1 — Sensori:**
- Sezione "Rilevati automaticamente": tabella sensori scoperti via MQTT non ancora configurati, con badge "NUOVO", pulsante "Accetta" (apre modal: assegna nome + zona + soglie)
- Sezione "Sensori configurati": AG-Grid editabile (nome, zona, attivo). Click su riga espande soglie individuali.
- Pulsante "Aggiungi manualmente" (apre modal con form: sensor_id, nome, zona)

**Tab 2 — Soglie:**
- Zone caricate da `GET /api/zones`. Per ogni zona: RangeSlider (min/max), mini-grafico live con threshold bands.
- Pulsante "Aggiungi zona": modal con input nome zona, selettore colore, min/max. Salva via `POST /api/zones`.
- Pulsante elimina zona (icona cestino): `DELETE /api/zones/{name}`. Disabilitato se sensori assegnati.

**Tab 3 — Email / Alert:**
- SMTP (host, porta, TLS, user, password, destinatari) + Test invio
- IMAP (host, porta, SSL, user, password, cartella, intervallo) + Test connessione
- Cooldown allarmi (minuti)

**Tab 4 — Generale:**
- Nome impianto, intervallo polling (minuti)
- **Archiviazione**: soglia archiviazione (giorni, default 180) — dati più vecchi vengono esportati in CSV e rimossi

**Tab 5 — Demo:**
- Scenario (6 opzioni), velocità (1x/10x/60x/600x), Start/Stop/Reset
- Banner demo sempre visibile quando attiva

**UX:** ogni tab ha il proprio pulsante Salva. Toast di conferma auto-dismiss 3s. Validazione inline sui campi.

**Nota:** il tab Database (backend switching TinyFlux↔TimescaleDB + migrazione) presente nella v1 viene rimosso intenzionalmente da Impostazioni e non appare in nessuna pagina v2. La scelta del database rimane configurabile solo via variabile d'ambiente `DATABASE_BACKEND` — operazione da sysadmin, non da utente UI.

### 4.5 Sistema (nuova pagina)

**Layout a 3 colonne:**

**Colonna 1 — Servizi (flex:1):**
- Card per ogni servizio (MQTT, APScheduler, Database):
  - Dot colorato + nome + stato testuale
  - Uptime (es. "attivo da 4h 12m")
  - MQTT e Scheduler: pulsanti Stop (se attivo) / Start (se fermo) / Restart (sempre)
  - Database: solo pulsante Restart (stop/start del pool non supportato)
  - Dettagli tecnici espandibili (es. broker address per MQTT, next_run per Scheduler)

**Colonna 2 — Log (flex:2):**
- Pannello terminale scuro (`#0f172a`), font monospace 11px
- Ultime 200 righe di log, auto-scroll
- Filtro rapido: ALL / INFO / WARNING / ERROR
- Colori: INFO=`#94a3b8`, WARNING=`#f59e0b`, ERROR=`#ef4444`
- Aggiornamento ogni 5s via polling

**Colonna 3 — Metriche (flex:1):**
- Uptime sistema (da `system.started_at` restituito da `GET /api/health`)
- Letture/ora (media ultima ora)
- Allarmi ultimi 7 giorni
- Dimensione database (da `db.size_mb` in `/api/health`)
- Versione backend
- **Ultima archiviazione**: data/ora + N righe archiviate (da `GET /api/archive/status`)
- **Pulsante "Archivia ora"**: esegue archiviazione manuale immediata via `POST /api/archive/run` (da `system.version` in `/api/health`)

---

## 5. Modifiche backend

### 5.1 Endpoint nuovi e modificati

**ESTESO** (esiste già in `main.py`, viene spostato in `routers/health.py` e arricchito):
```
GET  /api/health
     → {
         system: { started_at: ISO8601, uptime_s: int, version: str },
         mqtt:      { status: "connected"|"connecting"|"disconnected"|"error",
                      uptime_s: int, broker: str },
         scheduler: { status: "running"|"stopped"|"error",
                      uptime_s: int, next_run: ISO8601|null },
         db:        { status: "ok"|"degraded"|"error",
                      uptime_s: int, backend: "tinyflux"|"timescale", size_mb: float }
       }
     Nota: rimuovere l'implementazione semplice esistente in main.py e registrare questo router.
```

**NUOVI** in `routers/health.py`:
```
POST /api/services/mqtt/restart
POST /api/services/mqtt/stop
POST /api/services/mqtt/start

POST /api/services/scheduler/restart
POST /api/services/scheduler/stop
POST /api/services/scheduler/start

POST /api/services/db/restart
     Nota: Database NON supporta stop/start (pool sempre attivo).
     Solo restart (richiude e riapre il pool di connessione).
```

**NUOVO** in `routers/archive.py`:
```
GET  /api/archive/status
     → { last_run: ISO8601|null, last_rows_archived: int, archive_dir: str,
          files: [{ path: str, size_mb: float, from_date: date, to_date: date }] }

POST /api/archive/run
     → avvia archiviazione sincrona (entro timeout 30s) o asincrona se > 30s.
       Response: { status: "completed"|"running", rows_archived: int, files_written: [str] }
```

**NUOVO** in `routers/logs.py`:
```
GET  /api/logs?level=ALL|INFO|WARNING|ERROR&limit=200
     → [{ timestamp: ISO8601, level: str, service: str, message: str }]
```

**NUOVI/MODIFICATI** in `routers/sensors.py` (registrare `/discovered` PRIMA del path parametrico `/{sensor_id}` per evitare conflitti FastAPI):
```
GET  /api/sensors/discovered
     → [{ sensor_id: str, first_seen: ISO8601, last_seen: ISO8601, last_temp: float|null }]
     Nota: sensori rilevati via MQTT non ancora in sensors.json.

POST /api/sensors/{id}/accept
     body: { name: str, zone: str, min: float|null, max: float|null }
     → Passo 1: upsert sensore in sensors.json (riusa logica di PUT /api/sensors/{id}).
       Passo 2: se min/max forniti, aggiunge override in thresholds.sensors via
                config_service.update_sensor_threshold(). Le due scritture su config.json
                sono sequenziali non atomiche — in caso di errore al passo 2 il sensore
                risulta registrato senza override (comportamento accettabile).
     Naming: usa min/max (coerente con ZoneThresholds e SensorThresholdPatch esistenti).

DELETE /api/sensors/{id}
     → rimuove sensore da sensors.json e da thresholds.sensors (se presente).
       I dati storici (readings, alerts) vengono conservati nel DB. La UI mostra il
       sensor_id grezzo per le letture orfane (senza nome risolto).
```

**NUOVO** in `routers/config.py` (gestione zone):
```
GET  /api/zones
     → [{ name: str, color: str, threshold_min: float, threshold_max: float }]
     Nota: zone da thresholds.defaults; colori da AppConfig.zone_colors (dict[str,str]).

POST /api/zones
     body: { name: str, color: str, threshold_min: float, threshold_max: float }
     → aggiunge voce in thresholds.defaults E in zone_colors, scrive config.json.

DELETE /api/zones/{name}
     → rimuove da thresholds.defaults e zone_colors. Errore 409 se sensori assegnati.
```

**Modifiche al data model richieste:**
- `AppConfig` aggiunge campo `zone_colors: dict[str, str] = {"fridge": "#22c55e", "freezer": "#3b82f6"}` in `config_model.py`
- `ThresholdDefaultsPatch` in `config_model.py` deve essere reso generico: sostituire i campi hardcoded `fridge` e `freezer` con `zones: dict[str, ZoneThresholds] | None = None` per accettare zone arbitrarie. Il router `thresholds.py` (riga 45-46) usa `patch.fridge`/`patch.freezer` direttamente — deve essere aggiornato per iterare su `patch.zones.items()`.

**Persistenza zone_colors via ConfigService:**
`config_service.py` aggiunge due metodi analoghi a `update_threshold_defaults()`:
```python
def update_zone_color(self, zone_name: str, color: str) -> None:
    zone_colors = self._delta.get("zone_colors", {})
    zone_colors[zone_name] = color
    self._delta["zone_colors"] = zone_colors
    self._save_delta()

def delete_zone_color(self, zone_name: str) -> None:
    zone_colors = self._delta.get("zone_colors", {})
    zone_colors.pop(zone_name, None)
    self._delta["zone_colors"] = zone_colors
    self._save_delta()
```
`POST /api/zones` chiama `config_service.update_zone_color()` dopo aver scritto la zona in thresholds.
`DELETE /api/zones/{name}` chiama `config_service.delete_zone_color()`.

**Dimensione database via DatabaseAdapter:**
Aggiungere metodo astratto in `backend/database/adapter.py`:
```python
async def get_size_mb(self) -> float: ...
```
Implementazioni:
- `TinyFluxAdapter`: `os.path.getsize(self._path) / 1_048_576`
- `TimescaleAdapter`: query `SELECT pg_database_size(current_database()) / 1048576.0`

`GET /api/health` in `routers/health.py` accede al DB via `get_db()` da `dependencies.py` (non via `app.state`) — coerente con il pattern usato dagli altri router.

### 5.2 Robustezza backend

- **Tutti i router**: `try/except` con risposta `HTTPException` strutturata invece di crash 500
- **MQTT client**: espone `health_state` (`connected`/`connecting`/`disconnected`/`error`) e `discovered_sensors` (set in memoria). Al riavvio del backend il set `discovered_sensors` riparte vuoto — i sensori vengono ri-scoperti non appena il broker invia nuovi messaggi. Non è previsto TTL né dimensione massima del set.
- **APScheduler**: cattura eccezioni nei job, logga, non crasha il processo
- **Config service**: validazione schema su ogni `PATCH /api/config` prima di scrivere su disco
- **Archive service**: `backend/services/archive_service.py` — logica di archiviazione:
  1. Legge soglia da `config.archive_after_days` (default 180)
  2. Query DB: tutte le letture con `timestamp < now - archive_after_days`; idem per gli allarmi
  3. Raggruppa per mese (YYYY-MM), scrive `data/archive/YYYY-MM/readings.csv` e `data/archive/YYYY-MM/alerts.csv`
  4. Formato CSV readings: `timestamp,zone,sensor_id,temperature,humidity,battery`
  5. Formato CSV alerts: `timestamp,zone,sensor_id,temperature,level,message,resolved`
  6. Dopo scrittura verificata (file esiste + righe corrispondono), elimina dal DB le righe archiviate
  7. Aggiorna `data/archive/archive_log.json`: `{last_run, last_rows_archived, files}`
  8. `DatabaseAdapter` aggiunge metodo astratto `delete_readings_before(dt: datetime)` e `delete_alerts_before(dt: datetime)`
- **APScheduler job**: aggiunge job `archive_check()` giornaliero (ore 02:00) in `main.py` lifespan
- **Backend start_time**: aggiungere `app.state.started_at = datetime.utcnow()` nel lifespan startup di `main.py` (riga attuale non presente, deve essere inserita). Usato da `/api/health` per `system.uptime_s` e dalla pagina Sistema.
- **Service state via app.state**: i riferimenti a `_mqtt_client` e `_scheduler` (attualmente module-level globals in `main.py`) devono essere spostati su `app.state.mqtt_client` e `app.state.scheduler` nel lifespan startup, in modo che `routers/health.py` possa accedervi via `request.app.state` senza importazioni circolari.
- **log_collector**: implementare come `logging.Handler` personalizzato (`LogCollectorHandler`) con un `collections.deque(maxlen=1000)` thread-safe. Aggiungere l'handler al logger root in `main.py`. Ogni `LogRecord` viene convertito in `{timestamp, level, service, message}` dove `service = record.name` (nome del logger). `GET /api/logs` legge dal deque via `request.app.state.log_collector`.

### 5.3 Frontend resilienza

- Ogni callback che chiama il backend è wrappato in `try/except requests.exceptions`
- Stato di errore esplicito: card con bordo giallo + messaggio "Backend non raggiungibile" invece di eccezione non gestita
- Retry automatico al prossimo interval (no retry aggressivo)

---

## 6. Struttura file (delta rispetto all'attuale)

```
frontend/
  layout.py                  # MODIFICA: nuova sidebar 220px, dot status bottom
                             #   Aggiunge: dcc.Interval(id="interval-5s",  interval=5_000)
                             #             dcc.Interval(id="interval-30s", interval=30_000) [già esiste]
                             #             dcc.Interval(id="interval-60s", interval=60_000) [già esiste]
                             #   interval-5s  → system_callbacks SOLO log panel (GET /api/logs)
                             #   interval-30s → dashboard_callbacks + system_callbacks (health dots sidebar)
                             #   interval-60s → alerts_callbacks, settings_callbacks
  pages/
    dashboard.py             # RISCRIVI: zone cards dinamiche, tabella sensori
    history.py               # MODIFICA: statistiche % fuori soglia, filtri migliorati
    alerts.py                # MODIFICA: tema ag-theme-quartz, row coloring
    settings.py              # RISCRIVI: 5 tab, sensor discovery, add zone
    system.py                # NUOVO: pagina Sistema
  components/
    zone_card.py             # RISCRIVI: nuovo design, border-left, glow critico
    metric_card.py           # ELIMINA: sostituito da zone_card
    charts.py                # MODIFICA: colori zona automatici, light theme
    sensors_table.py         # NUOVO: tabella sensori compatta
    service_status.py        # NUOVO: componente card servizio
    log_panel.py             # NUOVO: pannello log terminale
  callbacks/
    dashboard_callbacks.py   # MODIFICA: zone dinamiche, resilienza API
    history_callbacks.py     # MODIFICA: statistiche % fuori soglia
    alerts_callbacks.py      # MODIFICA: row styling, ag-theme-quartz
    settings_callbacks.py    # RISCRIVI: sensor discovery, add zone, 5 tab
    system_callbacks.py      # NUOVO: health polling, service controls, logs

backend/
  routers/
    health.py                # NUOVO: GET /health, POST /services/{name}/restart|stop|start
    logs.py                  # NUOVO: GET /logs
    archive.py               # NUOVO: GET /archive/status, POST /archive/run
    sensors.py               # MODIFICA: GET /discovered, POST /{id}/accept, DELETE /{id}
                             #   ATTENZIONE: registrare /discovered PRIMA di /{sensor_id}
  services/
    mqtt_client.py           # MODIFICA: health_state, discovered_sensors set
    log_collector.py         # NUOVO: buffer circolare 1000 righe di log
    archive_service.py       # NUOVO: export CSV + delete DB + archive_log.json
  main.py                    # MODIFICA: registra nuovi router, aggiunge job archive ore 02:00
```

---

## 7. Requisiti tecnici

- **Tema Plotly**: `plotly_white` (sostituisce `plotly_dark`)
- **Tema AG-Grid**: `ag-theme-quartz` (sostituisce `ag-theme-alpine-dark`)
- **Bootstrap theme**: `FLATLY` o `COSMO` (light, sostituisce `SLATE`)
- **CSS custom**: variabili CSS per palette, nessun inline style nei componenti
- **Nessuna dipendenza aggiuntiva**: tutto realizzabile con le librerie già presenti in `requirements.txt`

---

## 8. Prerequisiti

Prima di iniziare lo sviluppo, eseguire questi passi di housekeeping sul branch corrente:
- Committare le modifiche pendenti: `frontend/app.py`, `requirements.txt`, `frontend/__init__.py`
- Creare il nuovo branch `feature/ui-redesign-v2` da `fix/bugfix-review`

## 9. Fasi di implementazione

1. **Design system** — `assets/custom.css` con variabili CSS, nuovo tema Bootstrap FLATLY, aggiorna `app.py`, aggiunge `interval-5s` in `layout.py`
2. **Nuovo layout** — sidebar 220px ridisegnata, dot status (aggiornati da `interval-30s`), routing invariato
3. **Backend health API** — estende `GET /api/health` in `routers/health.py`, aggiunge endpoint service controls, `routers/logs.py`, `log_collector.py`, modifica `mqtt_client.py` (health_state + discovered_sensors), registra `app.state.started_at`
4. **Backend zone API + sensor discovery** — `GET|POST|DELETE /api/zones` in `routers/config.py`, modifica `routers/sensors.py` (discovered, accept, delete)
5. **Dashboard** — zone_card v2 (dinamica da `/api/zones`), sensors_table, grafico light theme, resilienza API
6. **Pagina Sistema** — `pages/system.py`, `callbacks/system_callbacks.py`, componenti service_status + log_panel, polling `interval-5s`
7. **Impostazioni v2** — 5 tab, sensor discovery, add/delete zona
8. **Storico e Allarmi** — statistiche % fuori soglia, row coloring, ag-theme-quartz
9. **Robustezza frontend** — wrapping `try/except` in tutti i callback
10. **Robustezza backend** — error handling in tutti i router restanti
11. **Archiviazione dati** — `archive_service.py`, `routers/archive.py`, job APScheduler ore 02:00, pulsante "Archivia ora" in pagina Sistema, campo soglia in Impostazioni → Generale, metodi `delete_readings_before` / `delete_alerts_before` in entrambi gli adapter
12. **Test** — aggiorna test esistenti, aggiunge test per nuovi endpoint health/zones/sensors/archive
