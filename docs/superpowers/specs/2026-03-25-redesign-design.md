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

1. **Zone cards** — griglia dinamica (1 card per zona, `auto-fill minmax(280px, 1fr)`). Ogni card:
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
- Per ogni zona esistente: RangeSlider (min/max temperatura), mini-grafico live con threshold bands
- Pulsante "Aggiungi zona" (input nome zona, scelta colore)

**Tab 3 — Email / Alert:**
- SMTP (host, porta, TLS, user, password, destinatari) + Test invio
- IMAP (host, porta, SSL, user, password, cartella, intervallo) + Test connessione
- Cooldown allarmi (minuti)

**Tab 4 — Generale:**
- Nome impianto, intervallo polling (minuti), retention dati (giorni)

**Tab 5 — Demo:**
- Scenario (6 opzioni), velocità (1x/10x/60x/600x), Start/Stop/Reset
- Banner demo sempre visibile quando attiva

**UX:** ogni tab ha il proprio pulsante Salva. Toast di conferma auto-dismiss 3s. Validazione inline sui campi.

### 4.5 Sistema (nuova pagina)

**Layout a 3 colonne:**

**Colonna 1 — Servizi (flex:1):**
- Card per ogni servizio (MQTT, APScheduler, Database):
  - Dot colorato + nome + stato testuale
  - Uptime (es. "attivo da 4h 12m")
  - Pulsanti: Stop (se attivo) / Start (se fermo) / Restart (sempre)
  - Dettagli tecnici espandibili (es. broker address per MQTT, next_run per Scheduler, pool size per DB)

**Colonna 2 — Log (flex:2):**
- Pannello terminale scuro (`#0f172a`), font monospace 11px
- Ultime 200 righe di log, auto-scroll
- Filtro rapido: ALL / INFO / WARNING / ERROR
- Colori: INFO=`#94a3b8`, WARNING=`#f59e0b`, ERROR=`#ef4444`
- Aggiornamento ogni 5s via polling

**Colonna 3 — Metriche (flex:1):**
- Uptime sistema (dalla prima lettura in DB o dal boot)
- Letture/ora (media ultima ora)
- Allarmi ultimi 7 giorni
- Dimensione database
- Versione backend

---

## 5. Modifiche backend

### 5.1 Nuovi endpoint

```
GET  /api/health
     → { mqtt: {status, uptime_s, broker}, scheduler: {status, uptime_s, next_run},
          db: {status, uptime_s, backend, size_mb} }

POST /api/services/mqtt/restart
POST /api/services/scheduler/restart
POST /api/services/db/restart
POST /api/services/mqtt/stop
POST /api/services/mqtt/start
     (idem per scheduler)

GET  /api/logs?level=INFO&limit=200
     → [{ timestamp, level, service, message }]

GET  /api/sensors/discovered
     → sensori rilevati via MQTT ma non ancora in sensors.json

POST /api/sensors/{id}/accept
     body: { name, zone }
     → registra sensore in sensors.json

DELETE /api/sensors/{id}
     → rimuove sensore da sensors.json
```

### 5.2 Robustezza backend

- **Tutti i router**: `try/except` con risposta `HTTPException` strutturata invece di crash 500
- **MQTT client**: health state (`connected`, `connecting`, `disconnected`, `error`) esposto via `/api/health`
- **APScheduler**: cattura eccezioni nei job, logga, non crasha il processo
- **Config service**: validazione schema su ogni `PATCH /api/config` prima di scrivere su disco
- **Sensor discovery**: `mqtt_client` accumula in memoria i `sensor_id` rilevati non ancora in `sensors.json` → esposti via `GET /api/sensors/discovered`

### 5.3 Frontend resilienza

- Ogni callback che chiama il backend è wrappato in `try/except requests.exceptions`
- Stato di errore esplicito: card con bordo giallo + messaggio "Backend non raggiungibile" invece di eccezione non gestita
- Retry automatico al prossimo interval (no retry aggressivo)

---

## 6. Struttura file (delta rispetto all'attuale)

```
frontend/
  layout.py                  # MODIFICA: nuova sidebar 220px, dot status bottom
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
    sensors.py               # MODIFICA: GET /discovered, POST /{id}/accept, DELETE /{id}
  services/
    mqtt_client.py           # MODIFICA: health_state, discovered_sensors set
    log_collector.py         # NUOVO: buffer circolare 1000 righe di log
  main.py                    # MODIFICA: registra nuovi router
```

---

## 7. Requisiti tecnici

- **Tema Plotly**: `plotly_white` (sostituisce `plotly_dark`)
- **Tema AG-Grid**: `ag-theme-quartz` (sostituisce `ag-theme-alpine-dark`)
- **Bootstrap theme**: `FLATLY` o `COSMO` (light, sostituisce `SLATE`)
- **CSS custom**: variabili CSS per palette, nessun inline style nei componenti
- **Nessuna dipendenza aggiuntiva**: tutto realizzabile con le librerie già presenti in `requirements.txt`

---

## 8. Fasi di implementazione

1. **Setup e commit pending** — committa modifiche pendenti (`frontend/app.py`, `requirements.txt`), aggiunge `frontend/__init__.py`
2. **Design system** — `assets/custom.css` con variabili CSS, nuovo tema Bootstrap, aggiorna `app.py`
3. **Nuovo layout** — sidebar 220px ridisegnata, dot status, routing invariato
4. **Dashboard** — zone_card v2, sensors_table, grafico light theme
5. **Backend health API** — `routers/health.py`, `routers/logs.py`, `log_collector.py`, modifica `mqtt_client.py`
6. **Pagina Sistema** — `pages/system.py`, `callbacks/system_callbacks.py`, componenti service_status + log_panel
7. **Impostazioni v2** — 5 tab, sensor discovery, add zone
8. **Storico e Allarmi** — aggiornamenti minori (statistiche, row coloring, tema)
9. **Robustezza frontend** — wrapping try/except in tutti i callback
10. **Robustezza backend** — error handling in tutti i router
11. **Test** — aggiorna test esistenti, aggiunge test per nuovi endpoint
