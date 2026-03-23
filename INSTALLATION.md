# Guida all'installazione

medMonitor supporta due modalità di deploy:
- **Windows nativo** — esecuzione diretta senza Docker (consigliata per sviluppo)
- **Docker Compose** — deploy containerizzato (consigliato per produzione)

---

## Opzione A — Windows nativo (senza Docker)

### 1. Prerequisiti

#### Python 3.11+
Scarica da https://www.python.org/downloads/ e installa con l'opzione **"Add to PATH"** attiva.
```powershell
python --version   # verifica: Python 3.11.x o superiore
```

#### Mosquitto MQTT Broker
Scarica da https://mosquitto.org/download/ il pacchetto Windows (64-bit).
Installa con le opzioni di default. Il servizio parte automaticamente.
```powershell
# Verifica che il servizio sia attivo
sc query mosquitto
# oppure da Services (services.msc) → Mosquitto Broker → Running
```

Configurazione minima (`C:\Program Files\mosquitto\mosquitto.conf`):
```
listener 1883
allow_anonymous true
```
Riavvia il servizio dopo la modifica.

#### PostgreSQL (opzionale, solo se usi TimescaleDB)
Scarica da https://www.postgresql.org/downloads/windows/
Installa con pgAdmin e imposta la password dell'utente `postgres`.

### 2. Clone e configurazione
```powershell
gh repo clone greeneye71/medMonitor
cd medMonitor
copy .env.example .env
notepad .env
```

Parametri minimi in `.env`:
```ini
DATABASE_BACKEND=tinyflux
TINYFLUX_PATH=./data/temperature.db
MQTT_HOST=localhost
MQTT_PORT=1883
ZIGBEE_GATEWAY_IP=192.168.1.100

# Email SMTP (invio)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tua@email.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
ALERT_RECIPIENTS=destinatario@email.com

# Email IMAP (ricezione, opzionale)
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tua@email.com
IMAP_PASSWORD=xxxx_xxxx_xxxx_xxxx

# Soglie
FRIDGE_TEMP_MIN=0.0
FRIDGE_TEMP_MAX=30.0
FREEZER_TEMP_MIN=-30.0
FREEZER_TEMP_MAX=0.0
```

### 3. Ambiente virtuale e dipendenze
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Avvio servizi

Apri **tre terminali** separati (o usa Windows Terminal con tab):

**Terminale 1 — Backend FastAPI**
```powershell
cd medMonitor
venv\Scripts\activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminale 2 — Frontend Dash**
```powershell
cd medMonitor
venv\Scripts\activate
python frontend/app.py
```

**Terminale 3 — Mosquitto** (se non è un servizio Windows)
```powershell
mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v
```

### 5. Verifica

- Dashboard: http://localhost:8050
- API docs:   http://localhost:8000/docs
- MQTT:       porta 1883 (verifica con MQTT Explorer: https://mqtt-explorer.com/)

### 6. Avvio rapido con script batch (opzionale)

Crea un file `start.bat` nella root del progetto:
```batch
@echo off
title medMonitor

echo Avvio backend...
start "medMonitor Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

echo Avvio frontend...
start "medMonitor Frontend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python frontend/app.py"

echo.
echo medMonitor avviato!
echo   Dashboard: http://localhost:8050
echo   API docs:  http://localhost:8000/docs
echo.
pause
```

---

## Opzione B — Docker Compose

### 1. Prerequisiti

#### Docker Desktop per Windows
Scarica da https://www.docker.com/products/docker-desktop/
Requisiti: Windows 10/11 Pro/Home con WSL2 abilitato.

```powershell
# Abilita WSL2 (se non già fatto)
wsl --install

# Dopo l'installazione di Docker Desktop, verifica
docker --version
docker compose version
```

#### GitHub CLI
```powershell
winget install GitHub.cli
gh auth login
```

### 2. Clone e configurazione
```powershell
gh repo clone greeneye71/medMonitor
cd medMonitor
copy .env.example .env
notepad .env
```

Stessi parametri minimi della sezione Windows nativo, ma con `MQTT_HOST=mosquitto` (nome del container).

### 3. Avvio
```powershell
docker compose up -d
docker compose ps
```

Con TimescaleDB:
```powershell
docker compose --profile timescale up -d
```

### 4. Verifica

- Dashboard: http://localhost:8050
- API docs:   http://localhost:8000/docs

---

## Test con modalità demo

```powershell
curl -X POST http://localhost:8000/api/demo/start ^
  -H "Content-Type: application/json" ^
  -d "{\"speed\": \"10x\", \"scenario\": \"full_stress\"}"
```

Oppure da PowerShell:
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/demo/start `
  -ContentType "application/json" `
  -Body '{"speed": "10x", "scenario": "full_stress"}'
```

Apri http://localhost:8050 — vedrai il banner demo giallo.

## Backup

### TinyFlux
```powershell
copy data\temperature.db "backup_%date:~-4%%date:~3,2%%date:~0,2%.db"
```

### TimescaleDB (Docker)
```powershell
docker compose exec postgres pg_dump -U medmon medmonitor > backup.sql
```

### TimescaleDB (nativo)
```powershell
pg_dump -U medmon medmonitor > backup.sql
```
