# Demo Mode — Dati simulati per test usabilità

## Attivazione

Da API:
```bash
curl -X POST http://localhost:8000/api/demo/start \
  -H "Content-Type: application/json" \
  -d '{"speed": "10x", "scenario": "full_stress"}'
```

Da UI: Impostazioni > Demo > seleziona scenario e velocità > Avvia demo

## Scenari

| Scenario | Descrizione |
|---|---|
| `normal` | Temperature stabili, nessun allarme |
| `fridge_alarm` | Frigorifero sale sopra soglia (porta aperta simulata) |
| `freezer_alarm` | Freezer scende sotto soglia (guasto termostato) |
| `power_loss` | Entrambe le zone salgono per 2 ore (interruzione corrente) |
| `sensor_battery_low` | Batteria scende a 0, sensore va offline |
| `full_stress` | Tutti gli scenari in sequenza — demo completa |

Consigliato per primo test: `scenario=full_stress, speed=10x`
Simula 24 ore in circa 2 minuti, include allarmi e anomalie.

## Velocità simulazione

| Speed | 10 min reali simulati in |
|---|---|
| 1x | 10 minuti |
| 10x | 1 minuto |
| 60x | 10 secondi |
| 600x | 1 secondo (stress test) |

## Modello fisico generatore
```
next_temp = current
          + (base - current) * 0.05   ← mean reversion verso la base
          + gauss(0, 0.15)            ← rumore gaussiano naturale
          + scenario_drift            ← evento controllato dallo scenario
```

## Identificazione dati demo

I dati demo hanno sensor_id che inizia con `0xDEMO`.
Si cancellano con `POST /api/demo/reset` senza toccare i dati reali.

## Banner UI

Quando demo è attiva appare un banner giallo in cima a tutte le pagine:
"MODALITÀ DEMO — Scenario: X — Velocità: Yx" con pulsante "Ferma demo".

## Endpoint API demo
```
POST /api/demo/start   params: scenario, speed
POST /api/demo/stop
GET  /api/demo/status  → active, scenario, speed, step, temps correnti
POST /api/demo/reset   → cancella tutti i dati 0xDEMO*
```