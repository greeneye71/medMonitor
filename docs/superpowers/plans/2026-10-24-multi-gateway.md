# Multi-gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** medMonitor v2.1.0 gestisce più gateway Zigbee (un SONOFF Dongle-M per ambiente), ognuno con i suoi sensori, allarmi di gateway irraggiungibile e UI raggruppata per ambiente.

**Architecture:** Un registro `DATA_DIR/gateways.json` (scritto da `install.sh`, l'app lo modifica solo per rinominare) elenca i gateway; ognuno ha un'istanza zigbee2mqtt con il suo `base_topic` e `configuration.yaml`. Un solo client MQTT si iscrive a tutte le basi e tiene un `BridgeState` per gateway. Sensori e rilevati hanno `gateway_id`; il monitor valuta lo stato di ogni gateway prima dei sensori.

**Tech Stack:** FastAPI, Jinja2 + HTMX, SQLite, paho-mqtt v2, APScheduler, aiosmtplib, bash + Podman Quadlet.

**Spec:** `docs/superpowers/specs/2026-10-24-multi-gateway-design.md`

## Global Constraints

- Versione: `2.1.0` (`app/__init__.py: __version__`), CHANGELOG `## v2.1.0`.
- Gateway 1: container `zigbee2mqtt`, cartella `z2m`, base_topic `zigbee2mqtt`, frontend 8080, canale 11.
- Gateway n≥2: `zigbee2mqtt-n`, `z2m-n`, base `zigbee2mqtt_n`, porta 8079+n saltando UI_PORT, 8000, 1883; canale primo libero fra 11/15/20/25, poi 26. Id mai riusati.
- Fallback senza `gateways.json` (o invalido): `[Gateway(1, "Gateway 1", "zigbee2mqtt", Z2M_CONFIG, 8080)]`.
- Con un solo gateway UI ed email restano identiche a v2.0 (nessun nome ambiente nell'oggetto, niente select gateway, niente sezioni).
- Eventi gateway: `GATEWAY_OFFLINE_OPEN`, `GATEWAY_OFFLINE_CLOSE` (sensor_id NULL), `SENSOR_MOVED`.
- Oggetti email: `GATEWAY NON RAGGIUNGIBILE — <ambiente>`, `GATEWAY DI NUOVO RAGGIUNGIBILE — <ambiente>`; sensori con >1 gateway: `... — <Sensore> (<Ambiente>) ...`.
- Porta UI default 8090, mai 8000. Testi UI/doc in italiano. Commit `[feat]/[fix]/[docs]/[test]/[refactor]`, mai `.claude/settings.local.json`.
- Test: `.venv2/Scripts/python -m pytest -q`.

## Review Focus

1. Gateway irraggiungibile da prima dell'avvio dell'app (mai visto online): deve aprire l'allarme dopo `offline_minutes` dall'avvio, non mai. → Task 4 `test_gateway_never_online_opens_alarm`.
2. Gateway che torna online con cache z2m vecchia: i sensori non devono finire subito offline (grace su `back_at`). → Task 4 `test_grace_after_gateway_back`.
3. Stato cache di un gateway vecchio dopo spostamento sensore: non deve riportare indietro `gateway_id` né `last_temp`. → Task 3 `test_stale_cache_from_old_gateway_ignored`.
4. `gateways.json` corrotto/vuoto/con id duplicati: l'app parte col fallback, non crasha. → Task 1 `test_load_invalid_falls_back`.
5. Rimozione sensore/abbinamento con gateway id inesistente nel registro (POST manipolato o registro cambiato): 404/messaggio, non eccezione. → Task 9 `test_pair_unknown_gateway`.

---

### Task 1: Registro gateway e versione (effort: medium)

**Files:**
- Create: `app/gateways.py`, `tests/test_gateways.py`
- Modify: `app/__init__.py`, `app/main.py` (lifespan/create_app: `app.state.gateways`)

**Interfaces:**
- Produces: `@dataclass Gateway(id:int, name:str, base_topic:str, config:str, frontend_port:int=8080)`; `load(data_dir, fallback_config) -> list[Gateway]` (ordinato per id); `rename(data_dir, gid, name) -> None` (atomico tmp+`os.replace`, `KeyError` se id assente); `by_id(gateways, gid) -> Gateway | None`; `app.state.gateways: list[Gateway]`; `app.__version__ = "2.1.0"`.

- [ ] **Step 1: test** — `test_load_missing_fallback` (`[Gateway(1,"Gateway 1","zigbee2mqtt",cfg,8080)]`), `test_load_registry` (2 gateway, ordine per id, campi letti), `test_load_invalid_falls_back` (testo non JSON, `{}`, `{"gateways":[]}`, id duplicati, voce senza `base_topic` → fallback), `test_rename_atomic` (rinomina id 2, altri campi intatti, nessun `.tmp` residuo), `test_version` (`app.__version__ == "2.1.0"`).
- [ ] **Step 2:** run `pytest tests/test_gateways.py -q` → FAIL (modulo assente).
- [ ] **Step 3:** implementa `app/gateways.py`; `create_app` carica `app.state.gateways = gateways.load(data_dir, z2m_path)`.
- [ ] **Step 4:** run suite completa → PASS.
- [ ] **Step 5:** commit `[feat] Registro gateway e versione 2.1.0`.

### Task 2: Migrazione DB (effort: medium)

**Files:** Modify `app/db.py` (SCHEMA, `_migrate`), `tests/conftest.py`; Test `tests/test_db_settings.py`.

**Interfaces:**
- Produces: `sensors.gateway_id`, `discovered.gateway_id` INTEGER NOT NULL DEFAULT 1; tabella `gateway_state(gateway_id INTEGER PRIMARY KEY, offline_open INTEGER DEFAULT 0, offline_since TEXT, back_at TEXT, email_sent INTEGER DEFAULT 0)`; `add_sensor(..., gateway_id=1)`.

- [ ] **Step 1: test** — `test_migrate_adds_gateway_id`: DB creato con lo schema v2.0 (sensors/discovered senza colonna) + una riga; dopo `Database(path)` le righe hanno `gateway_id == 1` e `gateway_state` esiste. `test_migrate_idempotent` (doppia apertura ok).
- [ ] **Step 2:** FAIL. **Step 3:** colonne nello SCHEMA + `ALTER TABLE ... ADD COLUMN gateway_id INTEGER NOT NULL DEFAULT 1` se mancanti. **Step 4:** PASS suite.
- [ ] **Step 5:** commit `[feat] Colonne gateway_id e tabella gateway_state`.

### Task 3: MQTT multi-base (effort: high)

**Files:** Modify `app/mqtt.py`, `app/main.py`, `app/web/admin.py` (chiamate), `tests/test_mqtt.py`.

**Interfaces:**
- Consumes: `Gateway`, `gateway_state`.
- Produces:
  - `handle_message(db, states: dict[int, BridgeState], gateways: list[Gateway], topic, payload, now=None) -> None`; gateway = quello il cui `base_topic + "/"` è prefisso del topic (match più lungo).
  - `BridgeState` + `online_since: datetime|None`, `offline_since: datetime|None`.
  - Su `bridge/state`: transizione online→non online imposta `offline_since=now`; non online→online imposta `online_since=now` e scrive `gateway_state.back_at=iso(now)` (upsert).
  - `MqttService(db, host, port, gateways)`; `.states`; `.started_at`; `permit_join(gid, seconds=120)`, `remove_device(gid, ieee)`, `restart_bridge(gid)` → `bool` (False se gid sconosciuto).
  - Spostamento: sensore registrato attivo con `gateway_id != gid` e `seen > last_seen_at` → `UPDATE gateway_id, last_*`, evento `SENSOR_MOVED` (messaggio `"<nome>: da <vecchio> a <nuovo>"`), ritorna/salva richiesta di `remove_device(old_gid, ieee)` tramite callback `on_moved(old_gid, ieee)` opzionale. Se `seen <= last_seen_at`: ignora (né sensore né last_temp).
  - `discovered` upsert scrive `gateway_id=gid` (anche da `bridge/devices`).

- [ ] **Step 1: test** — adatta i test esistenti a `msg(db, states, topic, data, gws=GW1)`; nuovi: `test_two_bases_routed` (`zigbee2mqtt_2/bridge/state` online → solo `states[2].online`), `test_prefix_not_confused` (`zigbee2mqtt_2/x` non va al gateway 1), `test_discovered_gets_gateway_id`, `test_sensor_moved` (sensore gw1, messaggio più recente da gw2 → `gateway_id==2`, evento SENSOR_MOVED, callback `(1,"0x01")`), `test_stale_cache_from_old_gateway_ignored` (dopo spostamento, messaggio gw1 con last_seen vecchio → `gateway_id==2`, last_temp invariato), `test_back_at_written` (offline→online scrive `gateway_state.back_at`).
- [ ] **Step 2:** FAIL. **Step 3:** implementa; `_on_connect` iscrive 4 topic per gateway; `main.py` passa `app.state.gateways`; admin chiama le nuove firme (gid=1 provvisorio, Task 8/9 completano). **Step 4:** PASS suite.
- [ ] **Step 5:** commit `[feat] MQTT su più gateway e spostamento sensori`.

### Task 4: Monitor gateway (effort: high)

**Files:** Modify `app/monitor.py`, `app/main.py` (job), `tests/test_monitor.py`.

**Interfaces:**
- Consumes: `states`, `gateways`, `gateway_state`, `notifier.notify` kinds del Task 5 (in questo task i test controllano eventi e outbox count).
- Produces:
  - `evaluate_gateways(db, now, gateways, states, connected: bool, started_at) -> set[int]` ritorna gli id con bridge non online (per sopprimere email sensori). Offline per allarme se non online e `now - (offline_since or started_at) > offline_minutes`. Nessun allarme se `not connected` o se il gateway non ha sensori attivi non silenziati. Apertura: evento `GATEWAY_OFFLINE_OPEN` + notify `gateway_offline_open` (sensori elencati); chiusura quando online: `GATEWAY_OFFLINE_CLOSE` + notify `gateway_offline_close` solo se `email_sent`.
  - `run_cycle(db, now, gateways=None, states=None, connected=True, started_at=None)`; senza gateways comportamento v2.0 (i test vecchi passano).
  - Sensori: offline se `now - max(last_seen_at, back_at del suo gateway) > offline_minutes`; email offline soppressa se il gateway ∈ set ritornato (evento comunque); "di nuovo online" inviata solo se l'offline era stata inviata (flag in alert_state: riusa `offline_open` = 2 per "aperto con email"? → no: aggiungi colonna `offline_email INTEGER DEFAULT 0` via `_migrate`).

- [ ] **Step 1: test** — `test_gateway_offline_opens_after_minutes`, `test_gateway_never_online_opens_alarm` (mai online, started_at 40 min fa → OPEN), `test_gateway_close_sends_email`, `test_no_gateway_alarm_without_sensors`, `test_no_gateway_alarm_when_mqtt_disconnected`, `test_sensor_offline_email_suppressed_when_bridge_down` (evento OFFLINE sì, outbox no), `test_back_online_email_only_if_offline_sent`, `test_grace_after_gateway_back` (last_seen_at 2 h fa, back_at 5 min fa → non offline).
- [ ] **Step 2:** FAIL. **Step 3:** implementa; scheduler passa `app.state.mqtt.states/connected/started_at` e `app.state.gateways`. **Step 4:** PASS.
- [ ] **Step 5:** commit `[feat] Allarme gateway non raggiungibile e periodo di grazia`.

### Task 5: Notifiche con ambiente (effort: high)

**Files:** Modify `app/notifier.py`, `tests/test_notifier.py`.

**Interfaces:**
- Produces: `render(kind, sensor=None, now=None, ambiente=None, **ctx)`; kinds `gateway_offline_open(gateway, sensors, minutes)`, `gateway_offline_close(gateway, minutes)`. `notify(...)` invariato salvo `ambiente`. Il chiamante passa `ambiente` solo se `len(gateways) > 1`.
- Oggetto sensore con ambiente: `ALLARME TEMPERATURA — Frigo 2 (Ambulatorio) 9,2 °C`; corpo riga `Ambiente: Ambulatorio`. Email gateway: elenco sensori, suggerimenti (alimentazione/PoE, cavo, IP, `systemctl --user status <container>`).

- [ ] **Step 1: test** — `test_subject_with_ambiente`, `test_subject_single_gateway_unchanged`, `test_gateway_open_email` (oggetto esatto, nomi sensori e `zigbee2mqtt-2` nel testo), `test_gateway_close_email`.
- [ ] **Step 2–4:** FAIL → implementa (monitor passa `ambiente`) → PASS.
- [ ] **Step 5:** commit `[feat] Email con ambiente e notifiche gateway`.

### Task 6: /health (effort: medium)

**Files:** `app/main.py`, `tests/test_web.py`.
- Produces: `/health` campi esistenti + `gateway_online` (tutti i gateway con sensori attivi online), `gateways:[{id,name,online,sensors}]`, `version`.
- [ ] test `test_health_multi_gateway` → implementa → PASS → commit `[feat] /health con stato per gateway`.

### Task 7: Panoramica per ambiente (effort: medium)

**Files:** `app/web/routes.py`, `templates/overview.html`, `_cards.html`, `base.html`, `tests/test_web.py`.
- Produces: `overview_context` → `{"sections":[{"gateway","online","down_minutes","cards"}], "band", "now", "multi"}`; banda riassunto `"1 gateway non raggiungibile · 1 sensore fuori soglia"`; sezione vuota con link "Abbina un sensore"; footer `medMonitor v2.1.0`.
- [ ] test `test_overview_sections` (2 gateway, titoli e "non raggiungibile da"), `test_overview_single_gateway_unchanged` (nessun titolo sezione), `test_footer_version` → implementa → PASS → commit `[feat] Panoramica divisa per ambiente`.

### Task 8: Scheda Gateway (effort: medium)

**Files:** `app/web/admin.py`, `templates/settings/gateway.html`, `tests/test_web.py`.
- Produces: `GET /impostazioni/gateway` tabella (Ambiente/IP/Canale/Sensori/Stato+versione, Modifica, Prova) + riquadro spiegazione (testo spec §6.2) + `ssh -L <porta>:localhost:<porta>`; `POST /impostazioni/gateway/{gid}` (name → `gateways.rename`, ip/port/adapter/channel → yaml di quel gateway, CONFIG event, `restart_bridge(gid)`, avviso canale "Cambiarlo richiede di riabbinare i sensori"); `POST /impostazioni/gateway/{gid}/prova`. gid sconosciuto → 404.
- [ ] test `test_gateway_table_lists_all`, `test_gateway_edit_writes_own_yaml` (yaml gw2 cambiato, gw1 intatto, nome in gateways.json), `test_gateway_unknown_404` → implementa → PASS → commit `[feat] Scheda Gateway con più ambienti`.

### Task 9: Scheda Sensori (effort: medium)

**Files:** `app/web/admin.py`, `templates/settings/sensors.html`, `_discovered.html`, `tests/test_web.py`.
- Produces: select gateway (nascosta con 1 gateway) e hint; `POST abbina` con `gateway_id`; countdown per gateway; colonna Ambiente in sensori e rilevati (solo multi); aggiungi eredita `discovered.gateway_id`; rimuovi usa `remove_device(sensor.gateway_id, ieee)`.
- [ ] test `test_pair_on_selected_gateway`, `test_pair_unknown_gateway` (messaggio errore, nessun publish), `test_add_inherits_gateway`, `test_remove_uses_sensor_gateway` → implementa → PASS → commit `[feat] Sensori e abbinamento per gateway`.

### Task 10: Storico ed Eventi (effort: medium)

**Files:** `app/web/routes.py`, `templates/history.html`, `events.html`, `tests/test_web.py`.
- Produces: `<optgroup label="<ambiente>">` per gateway (solo multi); colonna Ambiente negli eventi (da sensore o, per eventi gateway, dal messaggio/gateway); etichette `GATEWAY_OFFLINE_OPEN` "Gateway non raggiungibile", `GATEWAY_OFFLINE_CLOSE` "Gateway di nuovo raggiungibile", `SENSOR_MOVED` "Sensore spostato".
- [ ] test `test_history_optgroup`, `test_events_labels` → implementa → PASS → commit `[feat] Storico ed Eventi con ambiente`.

Per poter mostrare l'ambiente degli eventi gateway, `add_event` per eventi gateway salva in `value` il gateway id (sensor_id NULL).

### Task 11: install.sh (effort: high, test manuale)

**Files:** `install.sh`.
- Migrazione: se `gateways.json` manca, chiede nome ambiente (default "Gateway 1") e lo scrive; yaml non toccato.
- Tabella riepilogo; menu `[A]ggiungi / [R]imuovi / [Invio] continua`.
- Aggiungi: nome, IP (+ porta 6638, adapter ember), id = max+1, base/porta/canale da Global Constraints, crea `~/medmonitor-data/z2m-n/configuration.yaml` (network_key/pan_id/ext_pan_id GENERATE, `frontend.port`), unit `zigbee2mqtt-n.container`.
- Rimuovi: non gateway 1; blocca se sensori attivi (sqlite3 se presente, altrimenti conferma esplicita); rinomina cartella `z2m-n.removed-<data>`, elimina unit.
- Rigenera `medmonitor.container` con volumi `~/medmonitor-data/z2m-n:/z2m-n:z`; daemon-reload, restart; health check per gateway (solo avviso).
- [ ] `bash -n install.sh` ok; prova a secco su copia (HOME temporanea) se possibile; commit `[feat] install.sh gestisce più gateway`.

### Task 12: Documentazione (effort: medium)

**Files:** `INSTALL.md` (sezione "Aggiungere un ambiente", rimozione, spostamento sensore), `HARDWARE.md` (un Dongle-M per ambiente, IP fisso; futuri SNZB-02M e SNZB-02UL), `CLAUDE.md` (architettura multi-gateway, gateways.json), `CHANGELOG.md` (`## v2.1.0`).
- [ ] commit `[docs] Documentazione multi-gateway v2.1.0`.

Dopo tutti i task: review completa del branch (effort xhigh).
