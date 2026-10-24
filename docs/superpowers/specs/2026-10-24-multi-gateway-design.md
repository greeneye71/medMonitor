# medMonitor — Più gateway Zigbee (uno per ambiente) — Specifica

Data: 2026-10-24 · Stato: in revisione
Base: `docs/superpowers/specs/2026-10-08-fedora-v2-design.md` (v2, un solo gateway).

## 1. Perché

Un gateway SONOFF Dongle-M copre un'area limitata. I frigoriferi e i congelatori da controllare stanno in ambienti diversi, lontani tra loro, ognuno con un cavo di rete. Oggi medMonitor gestisce un solo gateway, quindi copre un solo ambiente.

**Decisione dell'utente:** un gateway Ethernet per ogni ambiente, tutti nella stessa rete locale della VM. Sono previsti altri 3–4 ambienti, quindi 4–5 gateway in tutto. La soluzione con router Zigbee che estendono un'unica rete è stata scartata.

**Successo =**
- ogni ambiente ha il suo gateway e i suoi sensori, e tutti compaiono nella stessa medMonitor;
- in Panoramica si vede subito quale ambiente ha un problema, compreso un gateway non raggiungibile;
- per aggiungere un ambiente basta rilanciare `./install.sh` e rispondere a poche domande;
- l'aggiornamento di un'installazione esistente non richiede di riabbinare i sensori e non perde dati;
- la procedura è spiegata per intero in `INSTALL.md` e in breve nella UI.

## 2. Obiettivi, non-obiettivi, anti-obiettivi

**Obiettivi**
- N gateway (pensato per 1–6), ognuno con un nome di ambiente leggibile ("Laboratorio", "Magazzino").
- Ogni sensore appartiene a un gateway. L'abbinamento avviene sul gateway scelto.
- Panoramica divisa per ambiente (variante A approvata, §6.1).
- Scheda Impostazioni → Gateway con l'elenco dei gateway, la modifica di nome/IP/canale, la prova di connessione e un riquadro esplicativo (§6.2).
- Allarme email quando un gateway non risponde.
- Aggiunta e rimozione dei gateway tramite `./install.sh` (opzione A, scelta dall'utente).

**Non-obiettivi (per ora)**
- Altre grandezze misurate (umidità, temperatura ambiente, pressione, energia): progetto separato, vedi §10.
- Destinatari email diversi per ambiente o per tipo di misura: i destinatari restano gli stessi di oggi per tutti.
- Regole di allarme (N campioni, minuti offline, soglia batteria) diverse per ambiente: restano globali.
- Creare o eliminare un gateway dalla UI. Il container dell'app non può avviare servizi systemd sull'host.
- Spostare un sensore da un gateway all'altro senza resettarlo e riabbinarlo (è un limite di Zigbee).
- Router Zigbee o mesh tra ambienti.

**Anti-obiettivi (sarebbe un fallimento anche se "funziona")**
- Dover riabbinare i sensori già installati dopo l'aggiornamento.
- Perdere lo storico, gli eventi o le impostazioni esistenti.
- Una nuova esecuzione di `./install.sh` che rompe o riconfigura i gateway già presenti (deve restare idempotente).
- Una raffica di email quando un gateway cade (una per sensore più una per il gateway): vedi §5.3.
- Una UI più complicata per chi ha un solo gateway.

## 3. Vincoli

- Le regole di `CLAUDE.md` restano valide: porta UI scelta all'installazione (default 8090, mai 8000); Podman rootless + Quadlet; `.env` senza commenti inline; UI e documentazione in italiano; niente build frontend; prefissi di commit.
- Hardware per gateway: SONOFF Dongle-M, IP statico, `tcp://IP:6638`, adapter `ember`.
- Un'istanza di zigbee2mqtt gestisce un solo coordinator, quindi servono **N container zigbee2mqtt**. Mosquitto resta uno solo, condiviso.
- VM da 2 GB: ogni zigbee2mqtt occupa circa 100–150 MB, quindi 5 istanze ci stanno.

## 4. Architettura

```
Ambiente 1: SNZB-02LD ─Zigbee─▶ Dongle-M (IP .50) ─TCP─▶ zigbee2mqtt    ─┐ topic zigbee2mqtt/…
Ambiente 2: SNZB-02LD ─Zigbee─▶ Dongle-M (IP .51) ─TCP─▶ zigbee2mqtt-2  ─┼─▶ mosquitto ─▶ medmonitor
Ambiente 3: SNZB-02LD ─Zigbee─▶ Dongle-M (IP .52) ─TCP─▶ zigbee2mqtt-3  ─┘ topic zigbee2mqtt_3/…
```

### 4.1 Per ogni gateway

| Gateway | Container / unit Quadlet | Dati sull'host | `base_topic` | Frontend z2m (127.0.0.1) | Canale proposto |
|---|---|---|---|---|---|
| 1 (esistente) | `zigbee2mqtt` / `zigbee2mqtt.container` | `~/medmonitor-data/z2m` | `zigbee2mqtt` | 8080 | 11 (invariato) |
| 2 | `zigbee2mqtt-2` / `zigbee2mqtt-2.container` | `~/medmonitor-data/z2m-2` | `zigbee2mqtt_2` | 8081 | 15 |
| 3 | `zigbee2mqtt-3` | `~/medmonitor-data/z2m-3` | `zigbee2mqtt_3` | 8082 | 20 |
| 4 | `zigbee2mqtt-4` | `~/medmonitor-data/z2m-4` | `zigbee2mqtt_4` | 8083 | 25 |
| n | `zigbee2mqtt-n` | `~/medmonitor-data/z2m-n` | `zigbee2mqtt_n` | 8079+n | primo libero tra 11/15/20/25, poi 26 |

- Il gateway 1 mantiene nomi, percorsi e topic attuali. È questo che rende la migrazione indolore.
- Ogni gateway ha la sua rete Zigbee: `network_key`, `pan_id` ed `ext_pan_id` sono `GENERATE`, come oggi.
- Canali diversi riducono le interferenze. Il canale proposto si può cambiare durante l'installazione e dalla UI. *Scelta mia:* `install.sh` propone il primo canale non usato da un altro gateway.
- La porta del frontend z2m salta quelle occupate: `UI_PORT`, 8000, 1883. *Scelta mia.*
- Un id intero per ogni gateway (1, 2, 3…), mai riutilizzato dopo una rimozione. *Scelta mia.*

### 4.2 Registro dei gateway: `DATA_DIR/gateways.json`

È l'unica fonte di verità sull'**esistenza** dei gateway e sui loro **nomi**. Lo scrive `install.sh` sull'host (`~/medmonitor-data/app/gateways.json`). L'app lo legge e lo riscrive solo per cambiare il nome.

```json
{"gateways": [
  {"id": 1, "name": "Laboratorio", "base_topic": "zigbee2mqtt", "config": "/z2m/configuration.yaml", "frontend_port": 8080},
  {"id": 2, "name": "Magazzino", "base_topic": "zigbee2mqtt_2", "config": "/z2m-2/configuration.yaml", "frontend_port": 8081}
]}
```

- IP, porta, adapter e canale **non** stanno nel registro: si leggono e si scrivono nel `configuration.yaml` di ogni gateway con `app/z2m_config.py`, che già lavora per percorso.
- Se il file manca (installazione v2 non ancora migrata, sviluppo locale, test), l'app considera un solo gateway: `{"id":1,"name":"Gateway 1","base_topic":"zigbee2mqtt","config": Z2M_CONFIG}`. La variabile `Z2M_CONFIG` resta come fallback.
- L'app legge il registro all'avvio. `install.sh` riavvia comunque medmonitor dopo ogni modifica.

### 4.3 Container medmonitor

`install.sh` rigenera `medmonitor.container` con un volume per ogni gateway (`~/medmonitor-data/z2m-n:/z2m-n:z`, oltre a quello attuale `z2m:/z2m`), così l'app può leggere e scrivere ogni `configuration.yaml`.

## 5. Comportamento dell'app

### 5.1 MQTT (`app/mqtt.py`)

- Un solo client MQTT. Per ogni gateway del registro sottoscrive `<base>/bridge/devices`, `<base>/bridge/state`, `<base>/bridge/info` e `<base>/+`.
- Il gateway di un messaggio si ricava dal prefisso del topic. Al posto del singolo `BridgeState` c'è uno stato per gateway (online, versione, dispositivi, `permit_join_until`).
- `permit_join`, `remove_device` e `restart_bridge` ricevono il gateway e pubblicano su `<base>/bridge/request/...`.
- Le letture di un sensore aggiornano `sensors` come oggi (per `ieee`). *Scelta mia, spostamento di un sensore:* se un sensore registrato invia dati da un gateway diverso da quello memorizzato (cioè è stato resettato e riabbinato altrove), si aggiorna il suo `gateway_id`, si registra un evento informativo e l'app invia `remove_device` (force) al vecchio gateway, così non resta un dispositivo fantasma. Nome, soglie e storico restano intatti. Protezione: dopo un riavvio, il vecchio zigbee2mqtt rimanda lo stato in cache (`cache_state_send_on_startup`) e lo elenca in `bridge/devices`. Un messaggio da un gateway diverso conta solo se il suo `last_seen` è più recente del `last_seen_at` memorizzato, quindi lo stato in cache non fa tornare indietro il sensore né sovrascrive `last_temp`.

### 5.2 Dati (`app/db.py`, migrazione in `_migrate()`)

- `sensors.gateway_id INTEGER NOT NULL DEFAULT 1` e `discovered.gateway_id INTEGER NOT NULL DEFAULT 1`, con il solito schema `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`. I sensori esistenti finiscono sul gateway 1 senza fare nulla.
- Stato degli allarmi per gateway: o una tabella `gateway_state(gateway_id, offline_open, offline_since)`, o righe di `alert_state` con una chiave dedicata. Scelta lasciata al builder, purché lo stato resista a un riavvio come quello dei sensori.
- `samples`, `events`, `outbox` e `settings` non cambiano schema. Gli eventi del gateway usano `sensor_id` NULL oppure un riferimento al gateway, a scelta del builder.

### 5.3 Allarme "gateway non raggiungibile" (`app/monitor.py`, `app/notifier.py`)

- Un gateway è **offline** se il suo `bridge/state` non è `online` da più di `offline_minutes` (lo stesso parametro dei sensori, già in Impostazioni → Allarmi). Il controllo gira nel job di campionamento ogni 10 minuti.
- All'apertura: evento `GATEWAY_OFFLINE_OPEN` e un'email "GATEWAY NON RAGGIUNGIBILE — <ambiente>" che elenca i sensori coinvolti e suggerisce di controllare alimentazione/PoE, cavo di rete, IP e `systemctl --user status zigbee2mqtt-n`. Alla chiusura: evento `GATEWAY_OFFLINE_CLOSE` e un'email "GATEWAY DI NUOVO RAGGIUNGIBILE".
- *Scelta mia, anti-raffica:* dal momento in cui il `bridge/state` di un gateway non è più `online` (quindi già prima che si apra l'allarme gateway), le email "SENSORE NON RISPONDE" dei suoi sensori **non** vengono inviate. Gli eventi per sensore si registrano comunque. In questo modo nessuna email di sensore arriva prima di quella del gateway.
- **Decisione dell'utente, tempo di grazia al ritorno:** quando il gateway torna `online`, si salva l'ora del ritorno (`back_at`, persistente). Un sensore di quel gateway è offline solo se `now - max(last_seen_at, back_at) > offline_minutes`. Il conteggio quindi riparte da zero per tutti i sensori dell'ambiente, e partono solo le email dei sensori che restano davvero muti. Il compromesso è accettato: un sensore guastatosi durante il blackout viene segnalato fino a `offline_minutes` dopo il ritorno. L'email "di nuovo online" si invia solo per i sensori di cui era partita l'email offline.
- *Scelta mia:* l'allarme gateway si apre solo se il gateway ha almeno un sensore attivo e non silenziato. Un gateway appena aggiunto e vuoto, o un ambiente con tutti i sensori in manutenzione, non genera email. Lo stato offline si vede comunque in UI e in `/health`.
- Se il broker MQTT non è connesso, non si apre nessun allarme gateway: il problema riguarda tutti, e lo segnalano già il banner attuale e `/health`.
- Allarmi temperatura e batteria: invariati.

### 5.4 Email

- Tutte le email di un sensore indicano l'ambiente, per esempio oggetto `[medMonitor] ALLARME TEMPERATURA — Frigo 2 (Ambulatorio) 9,2 °C` e nel corpo la riga "Ambiente: Ambulatorio". *Scelta mia:* con un solo gateway l'ambiente non compare nell'oggetto, così chi ha un solo ambiente non vede cambiamenti.
- I destinatari sono gli stessi di oggi per ogni email.

### 5.5 `/health`

Restano i campi attuali. `gateway_online` è vero solo se sono online **tutti** i gateway con almeno un sensore attivo. Un gateway appena aggiunto e ancora vuoto non fa fallire la verifica finale di `install.sh`. Si aggiunge `gateways: [{"id","name","online","sensors"}]`. La verifica finale di `install.sh` mostra lo stato di ogni gateway e avvisa, senza bloccare, per quelli offline.

### 5.6 Archivio CSV

Formato invariato (`timestamp, sensor_id, sensor_name, temp_c, battery`). *Scelta mia:* niente colonna ambiente, per non mescolare intestazioni diverse nello stesso file mensile.

## 6. UI

### 6.1 Panoramica (variante A, approvata dall'utente)

- Una sezione per ogni gateway, nell'ordine del registro (ordine di aggiunta). L'intestazione mostra il nome dell'ambiente e lo stato del gateway: "in linea", oppure "non raggiungibile da X min" in rosso.
- Dentro ogni sezione, le schede sensore attuali (`_cards.html`) senza modifiche. Se il gateway non risponde, la sezione ha un bordo o un'intestazione rossa e le schede sono attenuate.
- Un gateway senza sensori mostra la sezione vuota con l'invito "Abbina un sensore" (link a Impostazioni → Sensori).
- La fascia di stato in alto riassume tutto, per esempio "1 gateway non raggiungibile · 1 sensore fuori soglia". Il banner attuale "gateway non connesso" (`routes.py:88`) diventa per gateway.
- **Con un solo gateway:** niente intestazioni di sezione, la pagina resta uguale a oggi. *Scelta mia.*
- Aggiornamento HTMX ogni 30 s come oggi.

Riferimento visivo: bozza "variante A" mostrata nel visual companion (sezioni Laboratorio / Magazzino / Ambulatorio).

### 6.2 Impostazioni → Gateway

1. **Riquadro "Come aggiungere o togliere un gateway"**, breve e sempre visibile. Testo indicativo:
   > Ogni ambiente ha il suo gateway (SONOFF Dongle-M) con indirizzo IP fisso e una propria rete Zigbee. Per aggiungerne uno: collegalo alla rete e assegnagli un IP fisso, poi sul server, nella cartella di medMonitor, esegui `./install.sh` e rispondi alle domande (nome dell'ambiente, IP). Lo script crea il servizio e lo avvia, e il nuovo gateway comparirà qui sotto. Per toglierlo si usa sempre `./install.sh`. Un sensore appartiene a un solo gateway: per spostarlo va resettato e riabbinato. Guida completa: `INSTALL.md`, sezione "Aggiungere un ambiente".
2. **Elenco gateway:** nome, IP, canale, numero di sensori, stato (online/offline, versione z2m), pulsanti **Modifica** e **Prova connessione**.
3. **Modifica** (pagina o riquadro espandibile per gateway): nome (salvato in `gateways.json`), IP, porta, adapter, canale (salvati nel `configuration.yaml` di quel gateway, come oggi). Al salvataggio di IP/canale si riavvia **solo** lo zigbee2mqtt di quel gateway (`<base>/bridge/request/restart`). Resta l'avviso sul canale ("Cambiarlo richiede di riabbinare i sensori").
4. Nota sul frontend z2m, per gateway: `ssh -L <porta>:localhost:<porta> utente@server`.

Riferimento visivo: bozza "Impostazioni · Gateway" mostrata nel visual companion.

### 6.3 Impostazioni → Sensori (abbinamento)

- Prima di "Avvia abbinamento" si sceglie il gateway dell'ambiente (con un solo gateway la scelta è nascosta). `permit_join` si invia solo a quel gateway, e il conto alla rovescia riguarda quel gateway.
- La lista "Da configurare" mostra l'ambiente di ogni dispositivo scoperto. Il sensore registrato eredita il `gateway_id` del dispositivo scoperto.
- L'elenco dei sensori registrati mostra la colonna Ambiente. "Rimuovi dalla rete" agisce sul gateway del sensore.

### 6.4 Storico ed Eventi

- Storico: nel selettore dei sensori, i sensori sono raggruppati per ambiente.
- Eventi: si aggiunge la colonna o etichetta Ambiente. Gli eventi del gateway compaiono con il nome dell'ambiente.

## 7. `install.sh`

Resta idempotente. Rilanciarlo senza aggiungere nulla deve lasciare tutto com'è (aggiorna immagine e unit, poi riavvia).

**Flusso**
1. Domande attuali (porta UI ecc.) e valori già presenti in `.env`.
2. **Migrazione**, se `gateways.json` non esiste: crea il registro con il gateway 1 (`z2m`, topic `zigbee2mqtt`, porta 8080, IP da `configuration.yaml` o da `GATEWAY_IP` in `.env`) e chiede il nome dell'ambiente (default "Gateway 1"). Non tocca `configuration.yaml` né la rete Zigbee.
   - Su un'installazione nuova: chiede nome e IP del primo gateway (come oggi solo l'IP) e crea il gateway 1.
3. **Riepilogo**: tabella con id, nome, IP, canale e stato del servizio per ogni gateway.
4. **Menu**: `[A]ggiungi gateway`, `[R]imuovi gateway`, `[Invio] continua`, ripetibile.
   - **Aggiungi:** chiede il nome dell'ambiente, l'IP (validato e non già usato) e il canale (proposto, modificabile). Prova la porta TCP 6638 e avvisa senza bloccare se non risponde. Crea `~/medmonitor-data/z2m-n/configuration.yaml` (stesso modello del gateway 1, con `base_topic`, `port` del frontend e `channel` del nuovo gateway) e `zigbee2mqtt-n.container`, aggiorna `gateways.json`.
   - **Rimuovi:** solo se il gateway non ha sensori attivi in medMonitor, altrimenti indica di rimuoverli prima da Impostazioni → Sensori. *Scelta mia:* lo script lo verifica leggendo il DB con `sqlite3` sull'host, se è installato, oppure chiedendo conferma esplicita. Ferma e cancella l'unit, toglie la voce dal registro, **lascia** la cartella dati (rinominata `z2m-n.removed-<data>`). Il gateway 1 non si può rimuovere. *Scelta mia, per semplicità.*
5. Rigenera `medmonitor.container` con i volumi di tutti i gateway, ricarica systemd e avvia/riavvia tutti i servizi.
6. Verifica finale: `/health` come oggi, più l'elenco dei gateway con il loro stato.

`.env`: `GATEWAY_IP` resta solo per compatibilità e migrazione, e non viene più scritto per i nuovi gateway.

## 8. Documentazione

- **`INSTALL.md`:** nuova sezione "Aggiungere un ambiente (un altro gateway)", passo per passo: IP statico del nuovo Dongle-M (rimanda alla sezione 2), `./install.sh` → `A`, risposte attese, verifica in Impostazioni → Gateway, abbinamento dei sensori scegliendo l'ambiente, prova. Poi "Togliere un ambiente", "Spostare un sensore in un altro ambiente" (reset del sensore, poi abbinamento sul gateway del nuovo ambiente: medMonitor lo riconosce, lo sposta da solo e lo toglie dal vecchio gateway; nome, soglie e storico restano) e, in "Risoluzione problemi", "un gateway non risponde" (comandi `systemctl --user status zigbee2mqtt-n`, `journalctl --user -u zigbee2mqtt-n`). Aggiornare "Cosa si installa", "Aggiornamento" (la migrazione è automatica e i sensori non si riabbinano) e "Backup" (includere `z2m-*` e `gateways.json`).
- **`HARDWARE.md`:** un Dongle-M per ambiente, ognuno con un IP fisso. Nota sulla RAM per 4–5 zigbee2mqtt.
- **`CLAUDE.md`:** schema dell'architettura con N gateway, registro `gateways.json`, topic per gateway.
- **`CHANGELOG.md`:** voce della nuova versione.
- **UI:** riquadro di §6.2.

## 9. Test

- `pytest` come oggi (`.venv2/Scripts/python -m pytest -q`).
- Da coprire: parsing dei topic con più `base_topic`; stato bridge per gateway; migrazione DB (un DB v2 esistente → sensori su gateway 1); registro mancante → fallback a un gateway; allarme gateway offline/online e soppressione delle email sensore (anche prima dell'apertura dell'allarme gateway); tempo di grazia al ritorno (nessuna email per i sensori che trasmettono entro `offline_minutes`, email per quelli ancora muti); nessun allarme per un gateway vuoto o con tutti i sensori silenziati; spostamento di un sensore (cambio `gateway_id`, `remove_device` al vecchio gateway, stato in cache più vecchio ignorato); abbinamento verso il gateway giusto; Panoramica con 1 gateway (come oggi) e con 3 (sezioni); `/health` con più gateway; rinomina dalla UI che aggiorna `gateways.json`.
- `install.sh`: provato a mano sul server (migrazione da v2 e aggiunta di un secondo gateway), con i passi descritti in `INSTALL.md`.

## 10. Evoluzione futura (progetto separato): altre grandezze

Più avanti medMonitor potrebbe misurare anche le condizioni degli ambienti e i consumi:
- umidità e temperatura dell'ambiente: sensori candidati **SONOFF AirGuard TH SNZB-02M** (temperatura, umidità, pressione dell'aria) e **SONOFF AirGuard SNZB-02UL** (temperatura e umidità, display E-Ink);
- energia elettrica consumata (sensore da scegliere).

Indicazioni per non ostacolare quel progetto:
- il multi-gateway non deve presupporre che ogni sensore sia un frigorifero o un congelatore. L'appartenenza a un gateway/ambiente è indipendente dal tipo di sensore (`kind`);
- la sezione per ambiente in Panoramica deve poter ospitare in futuro schede di tipo diverso;
- i destinatari email potranno differire per tipo di misura (per esempio frigoriferi a un gruppo, ambienti a un altro). Oggi restano unici, ma la scelta del destinatario va tenuta in un punto solo di `notifier.py`;
- i campi che zigbee2mqtt espone per SNZB-02M e SNZB-02UL (`humidity`, `pressure`, ecc.) andranno verificati sulla documentazione z2m all'inizio di quel progetto.

## 11. Lasciato al builder

- Struttura interna dello stato per gateway in `mqtt.py` e dello stato degli allarmi gateway nel DB (§5.2).
- Forma esatta della pagina o del riquadro "Modifica gateway" e stile delle sezioni in Panoramica, coerenti con il CSS attuale.
- Come `install.sh` legge e scrive `gateways.json` (per esempio `python3 -c` sull'host oppure `jq`, se presente). Deve funzionare su Fedora standard senza pacchetti extra.
