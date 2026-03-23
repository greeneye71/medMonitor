# Configurazione allarmi e notifiche

## Soglie di temperatura

Ogni sensore ha soglie proprie. I nuovi sensori ereditano il default di zona.

| Zona | Min default | Max default |
|---|---|---|
| Frigorifero | 0°C | +30°C |
| Freezer | -30°C | 0°C |

> Modifica le soglie per sensore: Impostazioni > Soglie temperatura

## Livelli di allarme

| Livello | Condizione | Azione |
|---|---|---|
| WARNING | Fuori soglia 0-15 min | Email con oggetto [AVVISO] |
| CRITICAL | Fuori soglia > 15 min | Email ogni 30 min con oggetto [ALLARME CRITICO] |

## Architettura email

medMonitor utilizza due protocolli per la gestione completa delle email:

- **SMTP** — invio allarmi, notifiche e report
- **IMAP** — ricezione conferme operatore, comandi via email, verifica delivery

### Flusso allarme completo
```
1. Sensore fuori soglia → Alert Engine genera allarme
2. SMTP invia email con ID univoco nell'oggetto
3. IMAP monitora risposte degli operatori
4. Operatore risponde con "ACK" → allarme confermato in dashboard
5. Operatore risponde con "MUTE 2h" → cooldown esteso a 2 ore
```

## Configurazione SMTP (invio)

### Server aziendale
```ini
SMTP_HOST=mail.azienda.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=allarmi@azienda.com
SMTP_PASSWORD=password_sicura
ALERT_RECIPIENTS=resp1@azienda.com,resp2@azienda.com
```

### Gmail (App Password)
1. Account Google > Sicurezza > Password per le app
2. In .env:
```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tuo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_RECIPIENTS=dest1@email.com,dest2@email.com
```

### Microsoft 365
```ini
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=tuo@azienda.com
SMTP_PASSWORD=password_app
```

## Configurazione IMAP (ricezione)

Il server IMAP è opzionale ma consigliato per abilitare:
- Conferma ricezione allarmi (ACK)
- Comandi via email (MUTE, ESCALATE)
- Verifica delivery

```ini
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=allarmi@azienda.com
IMAP_PASSWORD=password_sicura
IMAP_FOLDER=INBOX
IMAP_CHECK_INTERVAL_SECONDS=120
```

### Comandi via email

Gli operatori possono rispondere alle email di allarme con questi comandi:

| Comando | Descrizione |
|---|---|
| `ACK` | Conferma presa in carico dell'allarme |
| `MUTE 1h` / `MUTE 2h` | Silenzia gli allarmi per la durata indicata |
| `ESCALATE` | Inoltra l'allarme al livello superiore |
| `STATUS` | Richiedi stato attuale di tutti i sensori |

## Test email
```bash
# Test invio SMTP
curl -X POST http://localhost:8000/api/config/test-email \
  -H "Content-Type: application/json" \
  -d '{"email": "tuo@email.com"}'

# Test connessione IMAP
curl -X POST http://localhost:8000/api/config/test-imap
```

## Cooldown

Default: 30 minuti tra email successive per la stessa zona.
Modificabile in .env: `ALERT_COOLDOWN_MINUTES=30`
