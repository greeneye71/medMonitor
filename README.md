# medMonitor

Monitoraggio delle temperature di frigoriferi e congelatori (farmaci, vaccini, campioni)
con sensori Zigbee e allarmi via email. Gira su una VM Fedora con Podman rootless.

## Cosa fa

- Legge un campione ogni 10 minuti da ogni sensore Zigbee (SONOFF SNZB-02LD).
- Manda un'email quando un sensore resta fuori soglia per N campioni consecutivi
  (default 2), quando torna in soglia, quando va offline e quando ha la batteria scarica.
- Soglie min/max impostabili per ogni sensore, con valori proposti per frigorifero e congelatore.
- Storico con grafico ed esportazione CSV; i campioni vecchi vengono archiviati
  ogni notte in file CSV mensili.
- Impostazioni protette da password: sensori, email (SMTP e destinatari), gateway, allarmi, archivio.
- Gateway SONOFF Dongle-M collegato via Ethernet con IP statico (nessuna chiavetta USB).

## Architettura

```
SNZB-02LD ─Zigbee─▶ Dongle-M ─TCP 6638─▶ zigbee2mqtt ─▶ mosquitto ─▶ medmonitor ─▶ SQLite + CSV
                                                                         │
                                                                         ├─▶ UI web (porta scelta, default 8090)
                                                                         └─▶ email SMTP
```

Tre container gestiti da systemd tramite Quadlet: `mosquitto`, `zigbee2mqtt`, `medmonitor`.

| Componente | Tecnologia |
|---|---|
| Applicazione | Python 3.12, FastAPI, APScheduler, paho-mqtt, aiosmtplib |
| UI | Jinja2 + HTMX + ECharts, server-rendered, nessuna CDN |
| Dati | SQLite (`medmonitor.db`) + archivio CSV mensile |
| Deploy | Podman rootless + Quadlet su Fedora |

## Installazione

Vedi **[INSTALL.md](INSTALL.md)**. In breve, sulla VM Fedora:

```bash
git clone https://github.com/greeneye71/medMonitor.git ~/medmonitor
cd ~/medmonitor && ./install.sh
```

Hardware consigliato e requisiti della VM: [HARDWARE.md](HARDWARE.md).

## Sviluppo

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt        # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest -q
DATA_DIR=data .venv/bin/uvicorn app.main:create_app --factory --port 8090
```

Senza broker MQTT l'app parte comunque e mostra il gateway offline.
Password iniziale delle impostazioni: variabile `ADMIN_PASSWORD` (default `admin`).

La versione 1 (Plotly Dash, TinyFlux/TimescaleDB, Windows) è documentata in `docs/old/`.
