# medMonitor v2 — Specifica (Fedora, app unica)

Data: 2026-10-08 · Stato: in revisione

## 1. Obiettivo

Monitorare la temperatura di frigoriferi e congelatori per farmaci con sensori ZigBee e inviare email affidabili quando qualcosa non va. Installabile in pochi giorni su una VM Fedora, semplice da mantenere.

**Successo =**
- ogni sensore registrato produce un campione ogni 10 minuti visibile in dashboard;
- un sensore fuori soglia per N campioni consecutivi genera un'email entro N×10 minuti;
- sensore offline o batteria scarica generano un'email;
- tutta la configurazione operativa (email, destinatari, sensori, soglie, gateway) si fa dalla UI;
- installazione completa con un solo script seguendo `INSTALL.md`.

**Richiesto dall'utente:** VM Fedora; lettura ogni 10 min; email dopo N misure consecutive fuori range (default 2); email per offline e batteria scarica; archiviazione dati vecchi in CSV; UI moderna; impostazioni protette da password (SMTP, destinatari, sensori, soglie, gateway); porta UI scelta all'installazione; istruzioni dettagliate.

**Assunzioni:** < 20 sensori; VM in LAN con il gateway; VM già protetta (nessun hardening oltre la password admin); sistema mono-sito.

## 2. Hardware

- **Gateway:** SONOFF Dongle Max (Dongle-M), collegato in Ethernet/PoE con IP statico. zigbee2mqtt lo raggiunge via TCP: `tcp://<IP>:6638`, adapter `ember`.
- **Sensori:** SONOFF SNZB-02LD (sonda esterna, IP65). zigbee2mqtt espone `temperature` (°C), `battery` (%), `temperature_calibration`. Il sensore trasmette a variazione, non a intervallo fisso → l'app non dipende dalla cadenza del sensore (vedi §4).

## 3. Architettura

```
SNZB-02LD ──ZigBee──▶ Dongle-M ──TCP:6638──▶ zigbee2mqtt ──▶ mosquitto ──▶ medmonitor (FastAPI)
                                                                              ├─ SQLite (data/medmonitor.db)
                                                                              ├─ CSV archivio (data/archive/)
                                                                              ├─ SMTP (email)
                                                                              └─ UI web (porta scelta)
```

Tre container Podman rootless gestiti da systemd utente tramite Quadlet, su una rete Podman `medmonitor`:

| Container | Immagine | Porte esposte | Volumi |
|---|---|---|---|
| `mosquitto` | `docker.io/eclipse-mosquitto:2` | nessuna (solo rete interna) | `deploy/mosquitto/mosquitto.conf` |
| `zigbee2mqtt` | `docker.io/koenkk/zigbee2mqtt:2` | 8080 (UI z2m, per debug) | `~/medmonitor-data/z2m/` |
| `medmonitor` | `localhost/medmonitor:latest` (build locale, `python:3.12-slim`) | `UI_PORT` (default 8090) | `~/medmonitor-data/app/`, `~/medmonitor-data/z2m/` |

Tutti con `Restart=always`; avvio al boot con `loginctl enable-linger`.

### 3.1 Processo medmonitor

Un solo processo Python (uvicorn + FastAPI). Dentro:

| Modulo | Responsabilità |
|---|---|
| `app/main.py` | crea FastAPI, lifespan: init DB, avvia MQTT, avvia scheduler |
| `app/db.py` | schema SQLite (WAL), funzioni di accesso |
| `app/settings.py` | lettura/scrittura tabella `settings` con default |
| `app/mqtt.py` | client paho-mqtt (auto-reconnect nativo), parsing messaggi z2m, comandi bridge |
| `app/monitor.py` | logica pura: campionamento e valutazione allarmi (testabile senza I/O) |
| `app/notifier.py` | coda email (`outbox`) e invio SMTP |
| `app/archive.py` | esporta campioni vecchi in CSV mensili e li cancella dal DB |
| `app/z2m_config.py` | legge/scrive `configuration.yaml` di zigbee2mqtt |
| `app/auth.py` | password admin (hash `hashlib.scrypt`), sessione cookie |
| `app/web/` | route pubbliche e admin, template Jinja2, static (HTMX, ECharts, CSS, font) |

Dipendenze: `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `itsdangerous`, `apscheduler<4`, `paho-mqtt>=2`, `aiosmtplib`, `pyyaml`. DB con `sqlite3` della stdlib.

## 4. Flusso dati e allarmi

### 4.1 Ricezione MQTT

- Sottoscrizioni: `zigbee2mqtt/bridge/devices`, `zigbee2mqtt/bridge/state`, `zigbee2mqtt/bridge/info`, `zigbee2mqtt/+`.
- `bridge/devices` (retained) → mappa `friendly_name → ieee_address` e lista dispositivi abbinati.
- `zigbee2mqtt/<friendly_name>` con `temperature` → aggiorna in `sensors` del dispositivo (per `ieee`): `last_temp`, `last_battery` (se presente), `last_seen_at`. Se l'`ieee` non è registrato, finisce nella lista "Da configurare" (in memoria + tabella `discovered`).
- Riconnessione: `reconnect_delay_set(1, 60)` + `loop_start()` di paho. Stato connessione reale da `on_connect`/`on_disconnect`.

### 4.2 Campionamento (job ogni 10 minuti, allineato a :00, :10, …)

Per ogni sensore registrato e attivo:
1. se `last_seen_at` è più vecchio di **X minuti** (offline) → nessun campione;
2. altrimenti scrive `samples(sensor_id, ts=ora del job, temp_c=last_temp, battery=last_battery)`.

Poi esegue la valutazione allarmi (4.3). Intervallo fisso a 10 min (non configurabile).

### 4.3 Valutazione allarmi (stato persistito in `alert_state`)

Per ogni sensore, dopo il campionamento:

| Evento | Condizione apertura | Email apertura | Condizione chiusura | Email chiusura |
|---|---|---|---|---|
| `TEMP` | `consecutive_out ≥ N` (default 2). `consecutive_out` +1 per ogni campione fuori `[min,max]`, azzerato da un campione in range | ALLARME TEMPERATURA (valore, soglie, da quando) | primo campione in range | TEMPERATURA RIENTRATA (durata) |
| `OFFLINE` | `now − last_seen_at > X` min (default 120) | SENSORE NON RISPONDE | nuovo messaggio ricevuto | SENSORE DI NUOVO ONLINE |
| `BATTERY` | `last_battery < Y`% (default 20) | BATTERIA SCARICA | `last_battery ≥ Y+5`% | nessuna email (solo evento) |

- Ogni apertura/chiusura scrive una riga in `events` e accoda un'email in `outbox`.
- Un evento aperto non genera altre email finché non si chiude (nessun cooldown, nessun livello WARNING/CRITICAL).
- Nessun campione (sensore offline) non modifica `consecutive_out`.
- **Silenziamento:** se `sensors.muted_until > now`, gli eventi vengono comunque registrati ma le email non vengono accodate. Allo scadere, se un evento è ancora aperto, si accoda l'email di apertura.
- Riavvio: `alert_state` e `last_*` sono in SQLite → nessuna email persa o duplicata.

### 4.4 Email (`outbox`)

- Job ogni minuto: invia le righe `outbox` con `sent_at IS NULL`, una email per riga a tutti i destinatari.
- Errore SMTP → `attempts += 1`, `last_error` salvato, ritentato al giro dopo. Dopo 5 tentativi falliti si registra evento `EMAIL_ERROR` (visibile in Eventi e con banner rosso in Panoramica) e si continua a ritentare ogni 10 min.
- Sicurezza SMTP: `none` / `starttls` / `ssl` (aiosmtplib `start_tls` vs `use_tls`).
- Formato: HTML semplice + testo, in italiano. Oggetto: `[medMonitor] ALLARME TEMPERATURA — Frigo Farmacia 9.4 °C`.

### 4.5 Archiviazione

- Job notturno (03:00) + pulsante "Archivia ora".
- Campioni con `ts` più vecchio di **R giorni** (default 180) → appesi a `data/archive/AAAA-MM.csv` (colonne `timestamp,sensor_id,sensor_name,temp_c,battery`, timestamp ISO ora locale), file `fsync`, poi `DELETE` dal DB e `VACUUM` settimanale.
- Gli `events` non si archiviano (pochi).
- Storico in UI mostra solo i dati in DB; i CSV si scaricano dalla pagina Archivio.

## 5. Dati (SQLite, `data/medmonitor.db`, WAL)

```sql
sensors(ieee TEXT PRIMARY KEY, name TEXT, kind TEXT CHECK(kind IN ('fridge','freezer')),
        min_c REAL, max_c REAL, active INTEGER DEFAULT 1, muted_until TEXT,
        last_temp REAL, last_battery INTEGER, last_seen_at TEXT, created_at TEXT)
samples(sensor_id TEXT, ts TEXT, temp_c REAL, battery INTEGER)   -- index (sensor_id, ts)
events(id INTEGER PRIMARY KEY, ts TEXT, sensor_id TEXT, type TEXT, message TEXT, value REAL)
alert_state(sensor_id TEXT PRIMARY KEY, consecutive_out INTEGER DEFAULT 0,
            temp_open INTEGER DEFAULT 0, temp_since TEXT,
            offline_open INTEGER DEFAULT 0, battery_open INTEGER DEFAULT 0)
outbox(id INTEGER PRIMARY KEY, created_at TEXT, subject TEXT, body_text TEXT, body_html TEXT,
       attempts INTEGER DEFAULT 0, last_error TEXT, sent_at TEXT)
discovered(ieee TEXT PRIMARY KEY, friendly_name TEXT, model TEXT, first_seen TEXT, last_temp REAL)
settings(key TEXT PRIMARY KEY, value TEXT)   -- valore JSON
```

Orari salvati in UTC ISO-8601; mostrati in `Europe/Rome`.

Tipi `events.type`: `TEMP_OPEN`, `TEMP_CLOSE`, `OFFLINE_OPEN`, `OFFLINE_CLOSE`, `BATTERY_OPEN`, `BATTERY_CLOSE`, `MUTE`, `SENSOR_ADDED`, `SENSOR_REMOVED`, `EMAIL_ERROR`, `ARCHIVE`.

Rimozione sensore: riga `sensors` → `active=0` (sparisce da Panoramica e allarmi), campioni ed eventi restano.

### 5.1 Settings (chiavi e default)

| Chiave | Default |
|---|---|
| `smtp` | `{host:"", port:587, security:"starttls", user:"", password:"", sender:""}` |
| `recipients` | `[]` |
| `alarm` | `{consecutive_samples:2, offline_minutes:120, battery_percent:20}` |
| `presets` | `{fridge:{min:2,max:8}, freezer:{min:-25,max:-15}}` |
| `archive` | `{retention_days:180}` |
| `admin_password_hash` | da `ADMIN_PASSWORD` del `.env` al primo avvio |

Parametri gateway non stanno in `settings`: la fonte è `z2m/configuration.yaml`.

## 6. Gateway (zigbee2mqtt)

- `install.sh` crea `~/medmonitor-data/z2m/configuration.yaml` iniziale:
  ```yaml
  homeassistant: {enabled: false}
  mqtt: {base_topic: zigbee2mqtt, server: mqtt://mosquitto:1883}
  serial: {port: tcp://<GATEWAY_IP>:6638, adapter: ember}
  frontend: {enabled: true, port: 8080}
  advanced: {channel: 11, network_key: GENERATE, pan_id: GENERATE, ext_pan_id: GENERATE, last_seen: ISO_8601}
  ```
- Pagina **Gateway**: IP, porta, adapter, canale. "Salva" → `z2m_config.py` aggiorna solo `serial.port`, `serial.adapter`, `advanced.channel` (preserva il resto) e pubblica `zigbee2mqtt/bridge/request/restart`. Se z2m è giù, systemd lo riavvia e legge il file nuovo.
- Avviso in UI: cambiare il canale dopo aver abbinato sensori obbliga a riabbinarli.
- "Testa connessione": `socket.create_connection((ip, porta), timeout=3)` → OK/KO.
- Stato live: `bridge/state` (online/offline), versione da `bridge/info`, numero dispositivi.

## 7. Sicurezza e accesso

- Pagine pubbliche (Panoramica, Storico, Eventi) senza login.
- `/impostazioni/*` richiede sessione admin (cookie firmato `SessionMiddleware`, scadenza 8 h).
- Password admin: hash scrypt in `settings`; cambio da UI (richiede password attuale).
- Password SMTP in chiaro nel DB (VM protetta: accettato).

## 8. UI

Server-side: Jinja2 + HTMX (aggiornamenti parziali) + ECharts (grafici). Tutti gli asset (JS, CSS, font) inclusi nell'immagine, nessuna CDN. Italiano. Responsive (desktop + telefono). Tema chiaro di default, scuro con `prefers-color-scheme`. La direzione visiva viene definita con la skill di design in implementazione.

Colori di stato: OK verde, attenzione/batteria ambra, allarme rosso, offline grigio, silenziato blu-grigio.

### 8.1 Panoramica (`/`)
- Barra di stato in alto: "Tutto regolare" / "1 allarme attivo" / "Email non inviate" / "Gateway offline".
- Card per sensore: nome, temperatura grande, barra min–max con indicatore, sparkline 24 h, chip di stato, batteria, "ultimo dato N min fa", icona silenziato.
- Refresh HTMX ogni 30 s.

### 8.2 Storico (`/storico`)
- Selettore sensore + periodo (24 h, 7 g, 30 g, intervallo date).
- Grafico linea con banda soglie evidenziata e punti fuori range in rosso.
- Statistiche: min, max, media, % tempo in range, n° campioni.
- Export CSV del periodo.

### 8.3 Eventi (`/eventi`)
- Tabella paginata (50 righe), filtri sensore e tipo.

### 8.4 Impostazioni (`/impostazioni`, protetto)
Navigazione a schede:
1. **Sensori** — elenco (nome, tipo, min, max, batteria, ultimo dato, azioni modifica/silenzia/rimuovi). Sezione "Da configurare" con i dispositivi rilevati non registrati: nome + tipo (precompila min/max dai preset, modificabili) → "Aggiungi". Pulsante "Abbina nuovo sensore" → pubblica `zigbee2mqtt/bridge/request/permit_join` `{"time":120}` con countdown. Rimuovi → `active=0` + `zigbee2mqtt/bridge/request/device/remove` `{"id":"<ieee>","force":true}`. Silenzia: 1 h / 4 h / 24 h / annulla.
2. **Email** — server, porta, sicurezza, utente, password, mittente; destinatari (aggiungi/rimuovi); "Invia email di prova" (invio diretto, esito a schermo).
3. **Gateway** — §6.
4. **Allarmi** — N campioni consecutivi, minuti offline, % batteria, preset frigo/freezer.
5. **Archivio** — giorni di conservazione, "Archivia ora", elenco CSV scaricabili con dimensione, dimensione DB.
6. **Sicurezza** — cambio password admin.

## 9. Installazione

### 9.1 `install.sh` (idempotente, utente non root, sudo solo per firewall e linger)
1. Verifica Fedora + `podman` (se manca: istruzione `sudo dnf install -y podman`).
2. Chiede (con default dal `.env` esistente): porta UI (default 8090, verifica libera con `ss -ltn`, se occupata richiede), IP gateway, password admin (solo prima installazione).
3. Crea `~/medmonitor-data/{app,z2m,mosquitto}`, `.env` (`UI_PORT`, `ADMIN_PASSWORD`, `SECRET_KEY` generata, `TZ=Europe/Rome`), `configuration.yaml` z2m se assente.
4. `podman build -t medmonitor:latest .`
5. Genera i file Quadlet in `~/.config/containers/systemd/` (rete + 3 container) con la porta scelta.
6. `systemctl --user daemon-reload && systemctl --user restart …`; `sudo loginctl enable-linger $USER`; `sudo firewall-cmd --add-port=<porta>/tcp --permanent && --reload`.
7. Verifica finale: `curl -fs http://localhost:<porta>/health` e stampa URL.

Rilanciarlo = aggiornamento o cambio porta (chiude la porta vecchia nel firewall).

### 9.2 `INSTALL.md`
Passi numerati con comandi copiabili e un controllo "verifica" dopo ciascuno: prerequisiti Fedora; IP statico del Dongle-M (pagina web del dongle o prenotazione DHCP); clone repo; `install.sh`; primo accesso; configurazione gateway, email, primo sensore (abbinamento); prova allarme (soglie strette temporanee); aggiornamento (`git pull && ./install.sh`); backup (`~/medmonitor-data/`); risoluzione problemi (`systemctl --user status`, `journalctl --user -u medmonitor`, `podman ps`, log z2m). Scritto in modo che Claude Code sul server possa seguirlo; `CLAUDE.md` aggiornato di conseguenza.

### 9.3 Endpoint `/health`
JSON: `{db: ok, mqtt_connected, gateway_online, scheduler_running, outbox_pending}`.

## 10. Pulizia repo

Rimossi: `frontend/` (Dash), `backend/` (sostituito da `app/`), TinyFlux, TimescaleDB, IMAP, demo mode, `docker-compose.yml`, `docker/`, `*.bat`, `start.sh`, `crea_doc.py`; `requirements*.txt` riscritti per le nuove dipendenze. Spec e documenti v1 (`ARCHITECTURE.md`, `API.md`, `DATABASE_ADAPTER.md`, `CONFIGURATION.md`, `ALERTS.md`, `UI_DESIGN.md`, `DEMO_MODE.md`, `CLAUDE_PROMPTS.md`, `CLAUDE_SKILLS.md`, `CLAUDE_WORKFLOW.md`, vecchia spec redesign) → `docs/old/`. Restano aggiornati: `README.md`, `HARDWARE.md`, `INSTALL.md`, `CLAUDE.md`, `CHANGELOG.md`. Il branch/worktree `ui-redesign-v2` non viene toccato (abbandonato).

## 11. Test

pytest, senza rete né broker reali:
- `monitor.py`: N consecutivi apre/chiude, campione in range azzera, offline apre/chiude, offline non tocca il contatore, batteria con isteresi, silenziamento sopprime email e riaccoda alla scadenza, stato sopravvive a reload dal DB.
- parsing messaggi z2m (`bridge/devices`, messaggio sensore, payload senza `temperature` ignorato).
- `notifier.py`: retry e `EMAIL_ERROR` con SMTP finto.
- `archive.py`: CSV corretto, righe cancellate solo dopo scrittura, append su file esistente.
- `z2m_config.py`: aggiorna solo le chiavi previste.
- route: pagine pubbliche 200, impostazioni senza login → redirect, login errato/corretto.
UI verificata a mano nel browser.

## 12. Fuori ambito

Multi-utente/ruoli, HTTPS (LAN), notifiche non-email (SMS, Telegram), umidità, report PDF, migrazione dati v1 (assunto: il DB TinyFlux attuale contiene solo dati di prova), alta disponibilità.
