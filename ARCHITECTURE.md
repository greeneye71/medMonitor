# Architettura del sistema

## Principio chiave: Database Abstraction Layer

Due database intercambiabili senza modificare il codice applicativo:
- **TinyFlux** — Python puro, zero infrastruttura, default iniziale
- **TimescaleDB** — PostgreSQL esteso, produzione, alta scalabilità

## Schema generale
```
[Sensori ZigBee]
      | ZigBee 2.4GHz
      v
[Gateway Wi-Fi/Ethernet]   Sonoff ZBBridge Pro / SLZB-06
      | MQTT TCP/IP LAN
      v
[Mosquitto MQTT Broker]    Windows service / Docker
      | subscribe zigbee2mqtt/#
      v
[Backend FastAPI]
      |              |
      |              | APScheduler ogni minuto
      |              v
      |         [Alert Engine] --> SMTP/IMAP --> Email
      |
      | DatabaseAdapter (astratto)
      |_________________________
      |                         |
      v                         v
[TinyFlux]               [TimescaleDB]
file CSV locale           PostgreSQL+estensione
      |
      v
[Frontend Plotly Dash]    http://localhost:8050
```

## Database Abstraction Layer
```python
class DatabaseAdapter(ABC):
    async def write_reading(self, reading): ...
    async def get_readings(self, zone, from_dt, to_dt, limit): ...
    async def get_latest(self): ...
    async def write_alert(self, alert): ...
    async def get_alerts(self, limit): ...
    async def delete_demo_data(self): ...

# Factory: legge DATABASE_BACKEND da config
def get_adapter(settings) -> DatabaseAdapter:
    if settings.database_backend == "tinyflux":
        return TinyFluxAdapter(settings.tinyflux_path)
    return TimescaleAdapter(settings.postgres_dsn)
```

## Quando migrare a TimescaleDB

| Condizione | Azione |
|---|---|
| > 10 sensori attivi | Valutare migrazione |
| File TinyFlux > 500 MB | Pianificare migrazione |
| Query lente (> 2s) | Migrare |
| > 3 anni di dati | Migrare |

## Porte di rete

| Servizio | Porta |
|---|---|
| Dash frontend | 8050 |
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Mosquitto MQTT | 1883 |

## Stadi di scalabilità

- **Stadio 1**: TinyFlux, 2-5 sensori, 1 sede, Windows nativo o Docker locale
- **Stadio 2**: TimescaleDB, 10-50 sensori, 1-3 sedi, VPS / Docker Compose
- **Stadio 3**: InfluxDB/QuestDB, 100+ sensori, multi-sede, cloud