# Configurazione del sistema

## File .env
```ini
# ── Database ─────────────────────────────────────
DATABASE_BACKEND=tinyflux          # tinyflux | timescale
TINYFLUX_PATH=./data/temperature.db
POSTGRES_USER=medmon
POSTGRES_PASSWORD=cambia_questa_password
POSTGRES_DB=medmonitor
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# ── MQTT ─────────────────────────────────────────
MQTT_HOST=mosquitto
MQTT_PORT=1883

# ── Gateway ZigBee ───────────────────────────────
ZIGBEE_GATEWAY_IP=192.168.1.100

# ── Email SMTP (invio) ──────────────────────────
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tua@email.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
ALERT_RECIPIENTS=dest@email.com

# ── Email IMAP (ricezione/conferme) ─────────────
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tua@email.com
IMAP_PASSWORD=xxxx_xxxx_xxxx_xxxx
IMAP_FOLDER=INBOX
IMAP_CHECK_INTERVAL_SECONDS=120

# ── Applicazione ─────────────────────────────────
APP_NAME=medMonitor
APP_THEME=slate
LOG_LEVEL=INFO
POLLING_INTERVAL_MINUTES=10
ALERT_COOLDOWN_MINUTES=30
DATA_RETENTION_DAYS=365

# ── Soglie default di zona ────────────────────────
FRIDGE_TEMP_MIN=0.0
FRIDGE_TEMP_MAX=30.0
FREEZER_TEMP_MIN=-30.0
FREEZER_TEMP_MAX=0.0

# ── Demo ─────────────────────────────────────────
DEMO_MODE=false
DEMO_SPEED=10x
```

## Configurazione server di posta

### SMTP (invio allarmi e notifiche)

Il server SMTP è utilizzato per inviare email di allarme, notifiche e report.

| Parametro | Descrizione | Default |
|---|---|---|
| `SMTP_HOST` | Hostname del server SMTP | — (obbligatorio) |
| `SMTP_PORT` | Porta SMTP (587=STARTTLS, 465=SSL, 25=plain) | 587 |
| `SMTP_USE_TLS` | Abilita STARTTLS | true |
| `SMTP_USER` | Username autenticazione SMTP | — |
| `SMTP_PASSWORD` | Password autenticazione SMTP | — |
| `ALERT_RECIPIENTS` | Destinatari allarmi (virgola-separati) | — |

### IMAP (ricezione e conferme)

Il server IMAP è utilizzato per:
- **Conferma ricezione allarmi**: monitorare risposte degli operatori alle email di allarme
- **Comandi via email**: gli operatori possono inviare comandi (es. "ACK", "MUTE 2h") rispondendo alle email di allarme
- **Verifica delivery**: controllare che le email inviate siano state consegnate correttamente

| Parametro | Descrizione | Default |
|---|---|---|
| `IMAP_HOST` | Hostname del server IMAP | — (opzionale) |
| `IMAP_PORT` | Porta IMAP (993=SSL, 143=plain) | 993 |
| `IMAP_USE_SSL` | Abilita SSL/TLS | true |
| `IMAP_USER` | Username autenticazione IMAP | — |
| `IMAP_PASSWORD` | Password autenticazione IMAP | — |
| `IMAP_FOLDER` | Cartella da monitorare | INBOX |
| `IMAP_CHECK_INTERVAL_SECONDS` | Intervallo controllo nuove email (secondi) | 120 |

### Esempi di configurazione

#### Server aziendale (IMAP + SMTP sullo stesso server)
```ini
SMTP_HOST=mail.azienda.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=allarmi@azienda.com
SMTP_PASSWORD=password_sicura

IMAP_HOST=mail.azienda.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=allarmi@azienda.com
IMAP_PASSWORD=password_sicura
IMAP_FOLDER=INBOX
```

#### Gmail (App Password)
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tuo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tuo@gmail.com
IMAP_PASSWORD=xxxx xxxx xxxx xxxx
```

#### Microsoft 365 / Outlook
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

## Soglie per sensore individuale

Salvate in data/config.json, hanno priorità su .env.
```json
{
  "thresholds": {
    "defaults": {
      "fridge":  {"min": 0.0,   "max": 30.0},
      "freezer": {"min": -30.0, "max": 0.0}
    },
    "sensors": {
      "0x00158d0001234567": {
        "name": "Frigorifero sala A",
        "zone": "fridge",
        "min": 2.0, "max": 8.0,
        "override": true
      },
      "0x00158d0007654321": {
        "name": "Freezer sala B",
        "zone": "freezer",
        "min": null, "max": null,
        "override": false
      }
    }
  }
}
```

Logica di risoluzione:
- `override=True`  → usa min/max del sensore
- `override=False` → usa min/max del default di zona

## Priorità configurazione
```
1. data/config.json   (modifiche da UI — massima priorità)
2. .env               (configurazione iniziale)
3. valori default     (hardcodati in config.py)
```
