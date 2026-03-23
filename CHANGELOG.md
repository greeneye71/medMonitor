# Changelog

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