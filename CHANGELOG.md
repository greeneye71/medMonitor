# Changelog

## v2.1.1 — Email per sensore e correzioni
- Impostazioni → Sensori: interruttore **Email** per ogni sensore, spegne le email di quel sensore
  senza limite di tempo (eventi e allarmi restano registrati).
- Gli eventi dei gateway salvano l'ambiente in una colonna dedicata (migrazione automatica).
- Il ritorno del gateway azzera il conteggio offline dei sensori solo dopo un guasto vero,
  non al riavvio di medMonitor; anche una disconnessione da mosquitto conta come guasto.
- Spostamento di un sensore tra gateway solo con una lettura nuova (con `last_seen`), non con lo stato in cache.
- Email "sensore di nuovo raggiungibile" solo se era partita quella di guasto; email di rientro gateway sempre.
- Allarme gateway non aperto se tutti i suoi sensori hanno le email in pausa o spente.
- All'avvio vengono chiusi gli allarmi e rimossi i dati dei gateway tolti con `install.sh`.
- `gateways.json` con `base_topic` duplicati o non valido: avviso nel log e ripiego sul solo gateway 1.
- Modifica gateway: se la configurazione zigbee2mqtt non si scrive, il nome non viene cambiato.
- `/health` senza sensori considera tutti i gateway.
- `install.sh`: la porta del nuovo gateway salta anche quelle già occupate da altri programmi.

## v2.1.0 — Più gateway (uno per ambiente)
- Un gateway SONOFF Dongle-M per ogni ambiente, tutti nella stessa medMonitor. Registro in
  `~/medmonitor-data/app/gateways.json`; ogni gateway ha il suo container `zigbee2mqtt-N`, la sua rete Zigbee e il suo canale.
- `install.sh`: menu per aggiungere e rimuovere gateway (canale e porta assegnati in automatico,
  id mai riusati, cartella del gateway rimosso conservata); migrazione automatica da v2.0.
- Panoramica divisa per ambiente con stato del gateway; Storico ed Eventi mostrano l'ambiente.
- Impostazioni → Gateway: elenco dei gateway, modifica di nome/IP/canale per gateway, riavvio solo del gateway modificato.
- Abbinamento sul gateway scelto; un sensore resettato e riabbinato su un altro gateway viene spostato tenendo nome, soglie e storico.
- Allarme email "gateway non raggiungibile"; durante il guasto niente email offline dei suoi sensori, conteggio azzerato al ritorno.
- Email con il nome dell'ambiente quando i gateway sono più di uno.
- `/health` con lo stato di ogni gateway (`gateways`).
- Con un solo gateway UI ed email restano come in v2.0.

## v2.0.0 — Riscrittura per Fedora + Podman
Riscrittura completa e semplificata. La v1 (Dash, TinyFlux/TimescaleDB, Windows) non è più supportata;
la sua documentazione è in `docs/old/`.

- Una sola app FastAPI con UI server-rendered (Jinja2 + HTMX + ECharts), in italiano, tema chiaro/scuro.
- Dati in SQLite; campioni oltre il periodo di conservazione (default 180 giorni) archiviati ogni notte in CSV mensili.
- Campionamento ogni 10 minuti da zigbee2mqtt via MQTT.
- Allarmi email: N campioni consecutivi fuori soglia (default 2) con email di rientro,
  sensore offline, batteria scarica. Coda email con tentativi ripetuti e pausa temporanea delle email per singolo sensore.
- Soglie min/max per sensore con valori proposti per frigorifero e congelatore.
- Impostazioni protette da password: sensori (abbinamento dalla UI), email SMTP e destinatari,
  gateway SONOFF Dongle-M via Ethernet (IP, canale, prova connessione), regole di allarme, archivio.
- Deploy con Podman rootless e Quadlet: `install.sh` chiede porta UI (default 8090), IP del gateway
  e password, poi crea e avvia i servizi `mosquitto`, `zigbee2mqtt`, `medmonitor`.
- Guida di installazione passo-passo in `INSTALL.md`.
- Rimossi: modalità demo, IMAP, livelli WARNING/CRITICAL, TinyFlux/TimescaleDB, Docker Compose.

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