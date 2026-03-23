# Database Adapter

## Struttura file
```
backend/database/
├── adapter.py             # Classe astratta DatabaseAdapter (ABC)
├── factory.py             # get_adapter(settings)
├── tinyflux_adapter.py    # Implementazione TinyFlux
├── timescale_adapter.py   # Implementazione asyncpg
└── migrations/
    ├── 001_init.sql           # Schema TimescaleDB
    └── migrate_tinyflux.py    # Migrazione con --dry-run
```

## TinyFlux

Python puro, file CSV locale, nessuna infrastruttura.
```ini
DATABASE_BACKEND=tinyflux
TINYFLUX_PATH=./data/temperature.db
```

Limite consigliato: ~500.000 punti ≈ 3 anni con 2 sensori ogni 10 min.

## TimescaleDB
```ini
DATABASE_BACKEND=timescale
POSTGRES_USER=medmon
POSTGRES_PASSWORD=password_sicura
POSTGRES_DB=medmonitor
```

Schema principale:
```sql
CREATE TABLE temperature_readings (
    id          BIGSERIAL,
    zone        VARCHAR(20)  NOT NULL,
    sensor_id   VARCHAR(50)  NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity    DECIMAL(5,2),
    battery     SMALLINT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);
SELECT create_hypertable('temperature_readings', 'timestamp');
SELECT add_retention_policy('temperature_readings', INTERVAL '365 days');
```

## Migrazione TinyFlux → TimescaleDB
```bash
python backend/database/migrations/migrate_tinyflux.py \
  --tinyflux-path ./data/temperature.db \
  --postgres-dsn postgresql://user:pass@localhost/medmonitor \
  --dry-run
```

Rimuovi --dry-run per eseguire davvero.

## Confronto

| Caratteristica | TinyFlux | TimescaleDB |
|---|---|---|
| Setup | Nessuno | Docker + SQL |
| Linguaggio | Python puro | C / PostgreSQL |
| Max punti | ~500.000 | Illimitati |
| Query SQL | No | Completo |
| Backup | cp file | pg_dump |
| Adatto per | Inizio | Produzione |