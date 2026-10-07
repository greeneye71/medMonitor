# Changelog

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