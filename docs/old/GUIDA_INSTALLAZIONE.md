# Guida all'installazione — medMonitor

Questa guida accompagna passo-passo l'installazione di medMonitor su **Windows** o **Linux**.
Al termine avrai il sistema funzionante con dashboard accessibile dal browser.

---

## Indice

1. [Requisiti di sistema](#1-requisiti-di-sistema)
2. [Installazione dei prerequisiti](#2-installazione-dei-prerequisiti)
3. [Download del progetto](#3-download-del-progetto)
4. [Configurazione iniziale](#4-configurazione-iniziale)
5. [Configurazione email](#5-configurazione-email)
6. [Primo avvio](#6-primo-avvio)
7. [Verifica del funzionamento](#7-verifica-del-funzionamento)
8. [Collegamento hardware (sensori ZigBee)](#8-collegamento-hardware)
9. [Avvio automatico (servizio di sistema)](#9-avvio-automatico)
10. [Aggiornamento](#10-aggiornamento)
11. [Risoluzione problemi](#11-risoluzione-problemi)

---

## 1. Requisiti di sistema

| Componente | Requisito minimo |
|---|---|
| Sistema operativo | Windows 10/11 oppure Linux (Ubuntu 22.04+, Debian 12+, RHEL 9+) |
| RAM | 4 GB (consigliati 8 GB) |
| Disco | 10 GB liberi |
| Connessione di rete | LAN (per comunicare con il gateway ZigBee) |
| Browser | Chrome, Edge o Firefox aggiornato |

## 2. Installazione dei prerequisiti

### 2.1 Python 3.11 o superiore

<details>
<summary><strong>Windows</strong></summary>

1. Vai su https://www.python.org/downloads/
2. Scarica l'ultima versione di Python 3.x (3.11 o superiore)
3. Avvia l'installer
4. **IMPORTANTE**: spunta la casella **"Add Python to PATH"** nella prima schermata
5. Clicca "Install Now"

Per verificare l'installazione, apri un terminale (tasto Windows, scrivi `cmd`, Invio):
```
python --version
```
Dovresti vedere `Python 3.11.x` o superiore.

</details>

<details>
<summary><strong>Linux (Ubuntu / Debian)</strong></summary>

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip -y
```

Per verificare:
```bash
python3 --version
```
Dovresti vedere `Python 3.11.x` o superiore.

> **Nota:** Su Ubuntu 22.04 Python 3.10 e preinstallato. Se serve 3.11+:
> ```bash
> sudo add-apt-repository ppa:deadsnakes/ppa -y
> sudo apt update
> sudo apt install python3.11 python3.11-venv -y
> ```

</details>

<details>
<summary><strong>Linux (RHEL / Fedora / Rocky)</strong></summary>

```bash
sudo dnf install python3.11 python3.11-pip -y
```

</details>

### 2.2 Mosquitto MQTT Broker

Mosquitto e il servizio che riceve i dati dai sensori ZigBee.

<details>
<summary><strong>Windows</strong></summary>

1. Vai su https://mosquitto.org/download/
2. Scarica **Windows 64-bit** (file `.exe`)
3. Installa con le opzioni predefinite
4. Al termine, il servizio Mosquitto si avvia automaticamente

Per verificare:
```
sc query mosquitto
```
Lo stato deve essere `RUNNING`.

**Configurazione Mosquitto** (opzionale ma consigliata):

Apri il file `C:\Program Files\mosquitto\mosquitto.conf` con un editor di testo e assicurati che contenga:
```
listener 1883
allow_anonymous true
```
Se hai modificato il file, riavvia il servizio:
```
net stop mosquitto
net start mosquitto
```

</details>

<details>
<summary><strong>Linux (Ubuntu / Debian)</strong></summary>

```bash
sudo apt install mosquitto mosquitto-clients -y
```

Il servizio si avvia automaticamente. Per verificare:
```bash
sudo systemctl status mosquitto
```

**Configurazione Mosquitto** (opzionale ma consigliata):

```bash
sudo nano /etc/mosquitto/conf.d/medmonitor.conf
```
Inserisci:
```
listener 1883
allow_anonymous true
```
Riavvia:
```bash
sudo systemctl restart mosquitto
```

</details>

<details>
<summary><strong>Linux (RHEL / Fedora / Rocky)</strong></summary>

```bash
sudo dnf install mosquitto -y
sudo systemctl enable --now mosquitto
```

La configurazione e identica a Ubuntu (file in `/etc/mosquitto/conf.d/`).

</details>

### 2.3 Git (opzionale)

<details>
<summary><strong>Windows</strong></summary>

1. Vai su https://git-scm.com/downloads/win
2. Scarica e installa con le opzioni predefinite

</details>

<details>
<summary><strong>Linux</strong></summary>

```bash
# Ubuntu / Debian
sudo apt install git -y

# RHEL / Fedora
sudo dnf install git -y
```

</details>

In alternativa puoi scaricare il progetto come file ZIP (vedi sezione 3).

## 3. Download del progetto

### Opzione A — Con Git (consigliata)
```bash
git clone https://github.com/greeneye71/medMonitor.git
cd medMonitor
```

### Opzione B — Download ZIP
1. Vai su https://github.com/greeneye71/medMonitor
2. Clicca il pulsante verde **"Code"** > **"Download ZIP"**
3. Estrai il file ZIP in una cartella a tua scelta

**Windows:**
```
cd C:\medMonitor
```

**Linux:**
```bash
cd ~/medMonitor
```

## 4. Configurazione iniziale

### 4.1 Creare l'ambiente virtuale Python

L'ambiente virtuale isola le dipendenze di medMonitor dal resto del sistema.

**Windows:**
```
python -m venv venv
venv\Scripts\activate
```

**Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Il prompt del terminale mostrera `(venv)` all'inizio della riga.

### 4.2 Installare le dipendenze
```bash
pip install -r requirements.txt
```
L'installazione dura circa 1-2 minuti. Al termine vedrai un messaggio tipo "Successfully installed...".

### 4.3 Creare il file di configurazione

**Windows:**
```
copy .env.example .env
notepad .env
```

**Linux:**
```bash
cp .env.example .env
nano .env
```

**Parametri da configurare subito:**

| Parametro | Cosa inserire | Esempio |
|---|---|---|
| `ZIGBEE_GATEWAY_IP` | Indirizzo IP del gateway ZigBee nella tua rete | `192.168.1.100` |
| `SMTP_HOST` | Server per inviare email di allarme | `smtp.gmail.com` |
| `SMTP_USER` | Indirizzo email mittente | `allarmi@tuaazienda.com` |
| `SMTP_PASSWORD` | Password dell'email | `xxxx xxxx xxxx xxxx` |
| `ALERT_RECIPIENTS` | Chi riceve gli allarmi (separati da virgola) | `resp1@email.com,resp2@email.com` |

Gli altri parametri hanno gia valori predefiniti funzionanti. Li potrai modificare in seguito dalla dashboard.

Salva e chiudi il file.

## 5. Configurazione email

medMonitor usa due protocolli email:
- **SMTP** per **inviare** allarmi e notifiche
- **IMAP** (opzionale) per **ricevere** conferme dagli operatori

### 5.1 Gmail

1. Vai su https://myaccount.google.com/apppasswords
2. Genera una "Password per le app" per "Posta"
3. Inserisci in `.env`:
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tuo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx

# Opzionale — per ricevere conferme
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tuo@gmail.com
IMAP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 5.2 Microsoft 365 / Outlook

```ini
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tuo@azienda.com
SMTP_PASSWORD=password_app

IMAP_HOST=outlook.office365.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tuo@azienda.com
IMAP_PASSWORD=password_app
```

### 5.3 Server aziendale

```ini
SMTP_HOST=mail.azienda.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=allarmi@azienda.com
SMTP_PASSWORD=password

IMAP_HOST=mail.azienda.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=allarmi@azienda.com
IMAP_PASSWORD=password
```

## 6. Primo avvio

### Windows — Avvio rapido

Fai doppio clic su `start.bat` nella cartella del progetto.

Si apriranno due finestre di terminale:
- **medMonitor Backend** — il server API
- **medMonitor Frontend** — la dashboard web

Attendi qualche secondo che entrambi i servizi si avviino.

### Linux — Avvio rapido

```bash
chmod +x start.sh
./start.sh
```

Backend e frontend partiranno in background. Premi `Ctrl+C` per fermarli entrambi.

### Avvio manuale (entrambi i sistemi)

Se preferisci avviare manualmente, apri **due terminali** separati:

**Terminale 1 — Backend:**

| Windows | Linux |
|---|---|
| `venv\Scripts\activate` | `source venv/bin/activate` |

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminale 2 — Frontend:**

| Windows | Linux |
|---|---|
| `venv\Scripts\activate` | `source venv/bin/activate` |

```bash
python frontend/app.py
```

## 7. Verifica del funzionamento

1. Apri il browser e vai su **http://localhost:8050**
   - Dovresti vedere la dashboard medMonitor con il tema scuro

2. Verifica le API su **http://localhost:8000/docs**
   - Dovresti vedere la documentazione Swagger interattiva

3. **Prova la modalita demo** per verificare che tutto funzioni:
   - Nella dashboard, vai su **Impostazioni** > tab **Demo**
   - Seleziona scenario **"Stress test — tutti gli scenari"**
   - Velocita **"10x (consigliato)"**
   - Clicca **"Avvia demo"**
   - Torna alla **Dashboard**: vedrai temperature simulate e grafici in aggiornamento

4. **Testa l'invio email:**
   - Vai su **Impostazioni** > tab **Email**
   - Compila i campi SMTP con i tuoi dati
   - Clicca **"Test SMTP"**
   - Dovresti ricevere un'email di test

## 8. Collegamento hardware

### 8.1 Gateway ZigBee consigliati

| Gateway | Prezzo | Connessione |
|---|---|---|
| Sonoff ZBBridge Pro | ~22 EUR | Wi-Fi 2.4GHz |
| SLZB-06 | ~35 EUR | Ethernet (piu stabile) |

### 8.2 Sensori consigliati

| Sensore | Uso | Range | Prezzo |
|---|---|---|---|
| Sonoff SNZB-02D | Frigorifero | -20/+60°C | ~14 EUR |
| Aqara Temperature T1 | Freezer | -40/+85°C | ~16 EUR |

### 8.3 Configurazione del gateway

1. Collega il gateway alla rete Wi-Fi o Ethernet
2. Installa **Zigbee2MQTT** sul gateway (vedi documentazione del gateway)
3. Configura Zigbee2MQTT per connettersi al broker MQTT di medMonitor:
   - MQTT server: `IP_DEL_TUO_PC` (dove gira medMonitor)
   - MQTT port: `1883`
4. Effettua il pairing dei sensori tramite l'interfaccia del gateway
5. I sensori appariranno automaticamente nella dashboard di medMonitor

### 8.4 Verifica connessione sensori

Puoi verificare che i messaggi MQTT arrivino usando **MQTT Explorer**:
1. Scarica da https://mqtt-explorer.com/
2. Connettiti a `localhost:1883`
3. Dovresti vedere topic tipo `zigbee2mqtt/0x00158d...` con dati di temperatura

## 9. Avvio automatico

### Linux — Servizio systemd (consigliato per produzione)

Crea il file di servizio:

```bash
sudo nano /etc/systemd/system/medmonitor.service
```

Inserisci (modifica `User` e `WorkingDirectory` con i tuoi valori):

```ini
[Unit]
Description=medMonitor Temperature Monitoring
After=network.target mosquitto.service

[Service]
Type=forking
User=tuoutente
WorkingDirectory=/home/tuoutente/medMonitor
ExecStart=/bin/bash start.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Attiva il servizio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable medmonitor
sudo systemctl start medmonitor
```

Comandi utili:
```bash
sudo systemctl status medmonitor    # stato
sudo systemctl restart medmonitor   # riavvio
sudo journalctl -u medmonitor -f    # log in tempo reale
```

### Windows — Avvio automatico con Operazioni Pianificate

1. Apri **Utilita di pianificazione** (tasto Windows, scrivi "pianificazione")
2. Crea attivita di base:
   - Nome: `medMonitor`
   - Trigger: **All'avvio del computer**
   - Azione: **Avvia programma**
   - Programma: `C:\medMonitor\start.bat`
   - Directory di avvio: `C:\medMonitor`
3. Nelle proprieta, spunta **"Esegui anche se l'utente non e connesso"**

## 10. Aggiornamento

Per aggiornare medMonitor a una nuova versione:

**Windows:**
```
cd C:\medMonitor
git pull origin master
venv\Scripts\activate
pip install -r requirements.txt
```
Poi riavvia i servizi (chiudi e riapri `start.bat`).

**Linux:**
```bash
cd ~/medMonitor
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart medmonitor
```

## 11. Risoluzione problemi

### Il backend non si avvia

**Errore: `ModuleNotFoundError`**

| Windows | Linux |
|---|---|
| `venv\Scripts\activate` | `source venv/bin/activate` |

```bash
pip install -r requirements.txt
```

**Errore: `Address already in use` (porta 8000)**

Un altro processo usa la porta 8000. Trova e fermalo:

**Windows:**
```
netstat -ano | findstr :8000
taskkill /PID <numero_PID> /F
```

**Linux:**
```bash
sudo lsof -i :8000
sudo kill <PID>
```

### La dashboard non si apre

- Verifica che il backend sia in esecuzione (http://localhost:8000/docs)
- Verifica che la porta 8050 non sia bloccata dal firewall

**Linux — Aprire le porte nel firewall:**
```bash
# UFW (Ubuntu)
sudo ufw allow 8050/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 1883/tcp

# firewalld (RHEL/Fedora)
sudo firewall-cmd --permanent --add-port=8050/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=1883/tcp
sudo firewall-cmd --reload
```

### Non ricevo email di allarme

1. Vai su **Impostazioni** > **Email** > **Test SMTP**
2. Se il test fallisce:
   - Verifica host, porta e credenziali SMTP
   - Per Gmail: assicurati di usare una "Password per le app", non la password normale
   - Verifica che il firewall non blocchi la porta SMTP (587)

### I sensori non appaiono nella dashboard

**Windows:**
```
sc query mosquitto
```

**Linux:**
```bash
sudo systemctl status mosquitto
```

Poi:
1. Verifica che il gateway ZigBee sia connesso alla rete
2. Usa MQTT Explorer per verificare che arrivino messaggi su `zigbee2mqtt/#`
3. Controlla che `MQTT_HOST=localhost` e `MQTT_PORT=1883` in `.env`

### Backup dei dati

**TinyFlux** (file locale):

| Windows | Linux |
|---|---|
| `copy data\temperature.db backup.db` | `cp data/temperature.db backup.db` |

**TimescaleDB** (PostgreSQL):
```bash
pg_dump -U medmon medmonitor > backup.sql
```

---

*Documentazione medMonitor — Ultimo aggiornamento: marzo 2026*
