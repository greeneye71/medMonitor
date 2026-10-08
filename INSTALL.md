# Installazione di medMonitor su Fedora

Guida passo-passo per installare medMonitor su una VM Fedora con Podman rootless.
Ogni passo termina con un controllo **Verifica**: non proseguire finché non è superato.
La guida è scritta in modo che possa seguirla anche Claude Code direttamente sul server.

Tempo stimato: 30–45 minuti, più l'abbinamento dei sensori.

## Cosa si installa

Tre container gestiti da systemd (utente, non root) tramite Quadlet, su una rete Podman privata `medmonitor`:

| Servizio | Cosa fa | Porta sull'host |
|---|---|---|
| `mosquitto` | broker MQTT interno | nessuna |
| `zigbee2mqtt` | parla con il gateway Zigbee via rete (TCP 6638) | 8080 (diagnosi, solo `127.0.0.1`: da fuori via tunnel ssh) |
| `medmonitor` | campionamento, allarmi email, UI web | quella scelta (default **8090**) |

Dati persistenti in `~/medmonitor-data/`:

```
~/medmonitor-data/
├── app/            database SQLite (medmonitor.db) e archivio CSV (archive/AAAA-MM.csv)
└── z2m/            configuration.yaml e database di zigbee2mqtt (abbinamenti sensori)
```

---

## 1. Prerequisiti sulla VM

Serve Fedora (39 o successiva) con un utente normale che può usare `sudo`. Non lavorare come root.

```bash
sudo dnf install -y podman git curl
```

**Verifica**

```bash
podman --version        # podman version 4.x o 5.x
git --version
whoami                  # NON deve essere root
```

---

## 2. IP statico del gateway SONOFF Dongle-M

Il gateway va collegato alla rete Ethernet e deve avere un indirizzo IP fisso, altrimenti
zigbee2mqtt lo perde al primo riavvio del router. Due modi (sceglierne uno):

- **Prenotazione DHCP sul router** (consigliato): nella pagina del router associa il MAC
  del Dongle-M a un indirizzo fisso, poi riavvia il dongle.
- **IP statico sul dongle**: apri la pagina web del Dongle-M (l'IP attuale si vede nel
  router), sezione rete, imposta IP, maschera e gateway statici e salva.

Il firmware del dongle deve essere in modalità coordinatore Zigbee **EZSP/Ember** con
il server TCP sulla porta **6638** (impostazione di fabbrica).

**Verifica** (dalla VM, sostituisci l'IP):

```bash
ping -c 3 192.168.1.50
timeout 3 bash -c '</dev/tcp/192.168.1.50/6638' && echo "porta 6638 raggiungibile"
```

---

## 3. Scaricare medMonitor

```bash
cd ~
git clone https://github.com/greeneye71/medMonitor.git medmonitor
cd medmonitor
git checkout feature/fedora-v2      # finché la v2 non è unita al branch principale
```

**Verifica**

```bash
ls install.sh Containerfile app/main.py
```

---

## 4. Lanciare l'installazione

```bash
./install.sh
```

Lo script chiede:

| Domanda | Default | Note |
|---|---|---|
| Porta della UI web | 8090 | non sono ammesse 8000, 8080, 1883; se è occupata la richiede |
| IP del gateway Zigbee | — | quello fissato al passo 2 |
| Password di amministrazione | — | solo alla prima installazione; poi si cambia dalla UI |

Poi, senza altri interventi: crea `.env` e `~/medmonitor-data/`, scrive la configurazione
di zigbee2mqtt, costruisce l'immagine, genera i servizi Quadlet in
`~/.config/containers/systemd/`, li avvia, abilita l'avvio al boot (`loginctl enable-linger`,
chiede la password sudo) e apre la porta nel firewall.

Alla fine stampa l'indirizzo della UI, ad esempio `http://192.168.1.20:8090`.

**Verifica**

```bash
systemctl --user status mosquitto zigbee2mqtt medmonitor --no-pager | grep -E "●|Active"
curl -s http://localhost:8090/health        # usa la tua porta
```

Tutti e tre `active (running)`. `/health` restituisce un JSON con `"db": "ok"` e
`"mqtt_connected": true`. `"gateway_online": true` arriva quando zigbee2mqtt si è
collegato al dongle (pochi secondi; al primo avvio fino a un minuto).

---

## 5. Primo accesso

Apri da un PC della rete l'indirizzo stampato dallo script.

- **Panoramica**, **Storico** ed **Eventi** sono pubblici.
- **Impostazioni** chiede la password di amministrazione scelta al passo 4.

**Verifica**: la pagina si apre; in Impostazioni il login funziona.

---

## 6. Configurare il gateway

*Impostazioni → Gateway*: lo stato deve essere **online**. Il pulsante
"Prova connessione" prova a raggiungere `IP:6638`.

Se serve cambiare IP o canale, usa **Salva e riavvia**: medMonitor aggiorna
`configuration.yaml` e riavvia zigbee2mqtt. **Cambiare il canale dopo aver abbinato
i sensori obbliga a riabbinarli tutti.**

**Verifica**: stato gateway online, versione zigbee2mqtt visibile.

---

## 7. Configurare l'email

*Impostazioni → Email*:

1. Server SMTP, porta, sicurezza (STARTTLS per la porta 587, SSL/TLS per la 465,
   Nessuna per relay interni sulla 25), utente, password, mittente.
2. Aggiungi uno o più destinatari.
3. Premi **Invia email di prova**.

**Verifica**: l'esito appare a schermo e l'email arriva a tutti i destinatari
(controlla anche lo spam).

---

## 8. Abbinare il primo sensore (SNZB-02LD)

1. *Impostazioni → Sensori → Aggiungi sensore → Avvia abbinamento*: si apre una finestra di 120 secondi.
2. Sul sensore tieni premuto il pulsante finché il LED lampeggia (circa 5 s).
3. Entro pochi secondi il sensore compare sotto, come **Rilevato**, con la temperatura letta.
4. Dai un nome (es. "Frigo farmacia"), scegli il tipo (Frigorifero / Congelatore:
   le soglie si precompilano), correggi le soglie se serve e premi **Aggiungi**.

Ripeti per ogni sensore. Abbina i sensori vicino alla loro posizione finale.

**Verifica**: il sensore appare in Panoramica. Il primo campione entra nel database al
successivo multiplo di 10 minuti (:00, :10, :20…).

---

## 9. Prova di allarme

1. *Impostazioni → Sensori*, modifica un sensore e metti soglie strette che escludano la
   temperatura attuale (es. ambiente a 21 °C → min 2, max 8).
2. Aspetta **N campioni consecutivi** (default 2, quindi 20–30 minuti).
3. Deve arrivare l'email **ALLARME TEMPERATURA** e comparire l'evento in *Eventi*.
4. Rimetti le soglie corrette: al campione successivo arriva **TEMPERATURA RIENTRATA**.

**Verifica**: entrambe le email ricevute, due eventi registrati.

---

## Regole di allarme (riepilogo)

| Evento | Quando parte l'email | Quando si chiude |
|---|---|---|
| Temperatura | N campioni consecutivi fuori soglia (default 2, uno ogni 10 min) | primo campione in soglia (email di rientro) |
| Sensore offline | nessun dato da X minuti (default 120) | nuovo dato ricevuto (email) |
| Batteria scarica | sotto Y% (default 20) | sopra Y+5% (nessuna email) |

Un allarme aperto non manda altre email finché non si chiude. "Metti in pausa le email" (per qualche ora)
registra gli eventi ma non manda email; allo scadere, se l'allarme è ancora aperto, l'email parte.
Valori modificabili in *Impostazioni → Allarmi*.

---

## Aggiornamento

```bash
cd ~/medmonitor
git pull
./install.sh            # Invio su tutte le domande per tenere i valori attuali
```

Dati, sensori abbinati e impostazioni restano. Rilanciare `install.sh` serve anche per
cambiare porta: la vecchia viene chiusa nel firewall.

## Backup

Tutto lo stato è in `~/medmonitor-data/` più il file `~/medmonitor/.env`.

```bash
systemctl --user stop medmonitor zigbee2mqtt
tar czf ~/medmonitor-backup-$(date +%F).tar.gz -C ~ medmonitor-data medmonitor/.env
systemctl --user start zigbee2mqtt medmonitor
```

Copia l'archivio fuori dalla VM. Per ripristinare su una VM nuova: passi 1 e 3,
estrai l'archivio in `~`, poi `./install.sh`.

I campioni più vecchi del periodo di conservazione (default 180 giorni) finiscono ogni notte
in `~/medmonitor-data/app/archive/AAAA-MM.csv`, scaricabili da *Impostazioni → Archivio*.

---

## Risoluzione problemi

| Sintomo | Controllo |
|---|---|
| UI non raggiungibile da un altro PC | `curl localhost:PORTA/health` sul server; se risponde è il firewall: `sudo firewall-cmd --list-ports` |
| Servizio non parte | `systemctl --user status medmonitor` e `journalctl --user -u medmonitor -n 100` |
| Gateway offline | `journalctl --user -u zigbee2mqtt -n 100`; prova `timeout 3 bash -c '</dev/tcp/IP/6638'` |
| `mqtt_connected: false` | `systemctl --user status mosquitto`; `podman logs mosquitto` |
| Sensore non compare dopo l'abbinamento | finestra scaduta? Premi di nuovo "Avvia abbinamento" e ripremi il tasto del sensore; avvicinalo al gateway |
| Email non arrivano | avviso "Email di allarme non inviate" in Panoramica; *Eventi* filtrato su "Errore email" mostra l'errore SMTP |
| Servizi spenti dopo riavvio VM | `loginctl show-user $USER -p Linger` deve dire `Linger=yes` |
| Servizi Quadlet non generati | `/usr/libexec/podman/quadlet -dryrun -user` mostra gli errori nei file |

Comandi utili:

```bash
podman ps                                          # container in esecuzione
journalctl --user -u medmonitor -f                 # log in tempo reale
systemctl --user restart medmonitor                # riavvio singolo servizio
ssh -L 8080:localhost:8080 utente@vm               # UI zigbee2mqtt dal proprio PC
```
