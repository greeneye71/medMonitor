# medMonitor

Sistema di monitoraggio temperatura per celle frigorifere e freezer,
con dashboard web professionale e notifiche email automatiche.

## Caratteristiche principali

- Acquisizione dati da sensori ZigBee tramite gateway Wi-Fi/Ethernet
- Logging ogni 10 minuti (TinyFlux o PostgreSQL + TimescaleDB)
- Dashboard Plotly Dash professionale (tema dark/light)
- Soglie configurabili individualmente per ogni sensore
- Sistema di allarme email WARNING / CRITICAL con supporto IMAP/SMTP
- Modalità demo con 6 scenari simulati realistici
- Deploy: Windows nativo o Docker Compose

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

### Windows nativo (senza Docker)
```powershell
gh repo clone greeneye71/medMonitor
cd medMonitor
copy .env.example .env
# Modifica .env con le tue impostazioni
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Terminale 1: Backend
uvicorn backend.main:app --reload --port 8000

# Terminale 2: Frontend
python frontend/app.py
```

### Docker Compose
```powershell
gh repo clone greeneye71/medMonitor
cd medMonitor
copy .env.example .env
docker compose up -d
```

Dashboard: http://localhost:8050
API docs:  http://localhost:8000/docs

## Modello AI

Sviluppato con **claude-opus-4-6** tramite Claude Code.