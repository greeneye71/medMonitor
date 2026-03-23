# Documentazione API REST

Base URL: `http://localhost:8000/api`
Swagger UI: `http://localhost:8000/docs`

## Readings

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /readings | Letture con filtri (zone, from, to, limit) |
| GET | /readings/latest | Ultima lettura per ogni zona |

## Alerts

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /alerts | Storico allarmi |
| POST | /alerts/test | Invia email di test |

## Sensors

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /sensors | Lista sensori registrati |
| PUT | /sensors/{id} | Aggiorna nome/zona sensore |

## Thresholds (soglie per sensore)

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /thresholds | Defaults zona + soglie per sensore con effective_min/max |
| PATCH | /thresholds/defaults | Aggiorna default di zona |
| PATCH | /thresholds/sensor/{sensor_id} | Soglie individuali sensore |
| DELETE | /thresholds/sensor/{sensor_id} | Ripristina default zona |

Esempio PATCH soglie sensore:
```json
{ "min": -22.0, "max": -16.0, "override": true }
```

## Config

| Metodo | Endpoint | Descrizione |
|---|---|---|
| GET | /config | Configurazione completa |
| PATCH | /config | Aggiorna parametri runtime |
| POST | /config/test-email | Test SMTP (invio) |
| POST | /config/test-imap | Test IMAP (ricezione) |
| POST | /config/switch-database | Cambia backend DB |

## Demo

| Metodo | Endpoint | Descrizione |
|---|---|---|
| POST | /demo/start | Avvia demo (scenario, speed) |
| POST | /demo/stop | Ferma demo |
| GET | /demo/status | Stato corrente |
| POST | /demo/reset | Cancella dati demo |