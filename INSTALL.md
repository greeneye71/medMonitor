# Installazione di medMonitor su Fedora

Guida passo-passo per installare medMonitor su una VM Fedora con Podman rootless.
Ogni passo termina con un controllo **Verifica**: non proseguire finché non è superato.
La guida è scritta in modo che possa seguirla anche Claude Code direttamente sul server.

Tempo stimato: 30–45 minuti, più l'abbinamento dei sensori.

## Cosa si installa

Container gestiti da systemd (utente, non root) tramite Quadlet, su una rete Podman privata `medmonitor`:

| Servizio | Cosa fa | Porta sull'host |
|---|---|---|
| `mosquitto` | broker MQTT interno | nessuna |
| `zigbee2mqtt` | parla con il gateway Zigbee via rete (TCP 6638) | 8080 (diagnosi, solo `127.0.0.1`: da fuori via tunnel ssh) |
| `medmonitor` | campionamento, allarmi email, UI web | quella scelta (default **8090**) |
| `zigbee2mqtt-2`, `-3`… | uno per ogni ambiente in più (vedi [Aggiungere un ambiente](#aggiungere-un-ambiente)) | 8081, 8082… (solo `127.0.0.1`) |

Dati persistenti in `~/medmonitor-data/`:

```
~/medmonitor-data/
├── app/            database SQLite (medmonitor.db), registro gateway (gateways.json)
│                   e archivio CSV (archive/AAAA-MM.csv)
├── z2m/            configuration.yaml e database di zigbee2mqtt del gateway 1 (abbinamenti sensori)
└── z2m-2/, z2m-3/… lo stesso per ogni ambiente in più
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
| Nome dell'ambiente | Gateway 1 | solo la prima volta: il nome leggibile del gateway (es. "Laboratorio") |

Poi mostra l'elenco dei gateway configurati e chiede `[A]ggiungi gateway, [R]imuovi gateway,
[Invio] continua`. Per un solo ambiente premi Invio; per gli altri vedi
[Aggiungere un ambiente](#aggiungere-un-ambiente).

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

*Impostazioni → Gateway*: ogni gateway deve essere **In linea**. Il pulsante
"Prova connessione" prova a raggiungere `IP:6638` di quel gateway.

Nome dell'ambiente, IP o canale si cambiano nel riquadro **Modifica** del gateway con
**Salva e riavvia**: medMonitor aggiorna il suo `configuration.yaml` e riavvia solo il
suo zigbee2mqtt. **Cambiare il canale dopo aver abbinato
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

1. *Impostazioni → Sensori → Aggiungi sensore*: con più gateway scegli prima l'ambiente in cui si trova
   il sensore, poi **Avvia abbinamento**: si apre una finestra di 120 secondi, solo su quel gateway.
2. Sul sensore tieni premuto il pulsante finché il LED lampeggia (circa 5 s).
3. Entro pochi secondi il sensore compare sotto, come **Rilevato**, con la temperatura letta.
4. Dai un nome (es. "Frigo farmacia"), scegli il tipo (Frigorifero / Congelatore:
   le soglie si precompilano), correggi le soglie se serve e premi **Aggiungi**.

Ripeti per ogni sensore. Abbina i sensori vicino alla loro posizione finale, sul gateway del loro ambiente.

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
| Gateway non raggiungibile | gateway non in linea da X minuti e con almeno un sensore attivo | gateway di nuovo in linea (email) |

Quando un gateway non risponde non partono le email "sensore non risponde" dei suoi sensori:
arriva solo quella del gateway. Al ritorno il conteggio offline dei suoi sensori riparte da zero.
Con più gateway oggetto e corpo delle email indicano l'ambiente.

Un allarme aperto non manda altre email finché non si chiude. "Metti in pausa le email" (per qualche ora)
registra gli eventi ma non manda email; allo scadere, se l'allarme è ancora aperto, l'email parte.
Valori modificabili in *Impostazioni → Allarmi*.

---

## Aggiungere un ambiente

Ogni ambiente lontano dagli altri ha il suo gateway SONOFF Dongle-M, con una propria rete Zigbee.
Tutti i gateway stanno nella stessa rete locale della VM e compaiono nella stessa medMonitor.

1. Collega il nuovo Dongle-M alla rete dell'ambiente e assegnagli un **IP fisso** come al passo 2.
   **Verifica** dalla VM: `timeout 3 bash -c '</dev/tcp/IP/6638' && echo ok`.
2. Sul server:
   ```bash
   cd ~/medmonitor
   ./install.sh            # Invio sulle domande già note
   ```
3. All'elenco dei gateway premi **A**, scrivi il nome dell'ambiente (es. "Ambulatorio") e l'IP.
   Lo script sceglie da solo:
   - il numero del gateway (2, 3…, mai riusato dopo una rimozione);
   - il canale Zigbee, il primo libero tra 11, 15, 20 e 25 (poi 26); si può cambiare da
     *Impostazioni → Gateway* **prima** di abbinare i sensori;
   - la porta dell'interfaccia di zigbee2mqtt (8081, 8082…, saltando quelle occupate).
4. Premi Invio per continuare: lo script crea `~/medmonitor-data/z2m-N/`, il servizio
   `zigbee2mqtt-N`, aggiorna `medmonitor` e riavvia tutto.
5. Abbina i sensori dell'ambiente (passo 8) scegliendo il nuovo gateway.

**Verifica**: in *Impostazioni → Gateway* il nuovo gateway è **In linea**;
`systemctl --user status zigbee2mqtt-N` è `active (running)`; in Panoramica compare la
sezione del nuovo ambiente.

Con un solo gateway Panoramica ed email restano come prima, senza nomi di ambiente.

### Rimuovere un gateway

1. *Impostazioni → Sensori*: rimuovi prima tutti i sensori di quel gateway.
2. `./install.sh`, all'elenco dei gateway premi **R** e scrivi il numero del gateway.

Lo script ferma e cancella il servizio `zigbee2mqtt-N` e sposta la sua cartella in
`~/medmonitor-data/z2m-N.removed-DATA` (rete Zigbee e abbinamenti conservati, eliminabile a mano).
Il gateway 1 non si può rimuovere: nome e IP si cambiano da *Impostazioni → Gateway*.
Se il database non è leggibile lo script chiede di scrivere `RIMUOVI` per confermare.

### Spostare un sensore in un altro ambiente

Un sensore Zigbee appartiene a una sola rete: per spostarlo va resettato e riabbinato.

1. Porta il sensore nel nuovo ambiente.
2. *Impostazioni → Sensori → Aggiungi sensore*, scegli il gateway del nuovo ambiente, **Avvia abbinamento**.
3. Tieni premuto il pulsante del sensore finché il LED lampeggia (il reset e l'abbinamento sono la stessa operazione).

medMonitor riconosce il sensore: nome, soglie e storico restano, cambia solo l'ambiente.
Il vecchio gateway lo dimentica da solo e in *Eventi* resta traccia dello spostamento.

---

## Aggiornamento

```bash
cd ~/medmonitor
git pull
./install.sh            # Invio su tutte le domande per tenere i valori attuali
```

Dati, sensori abbinati, gateway e impostazioni restano. Rilanciare `install.sh` serve anche per
cambiare porta (la vecchia viene chiusa nel firewall) e per aggiungere o togliere gateway.
Un'installazione v2.0 con un solo gateway viene migrata da sola: lo script chiede solo il nome
dell'ambiente e non tocca la rete Zigbee.

## Backup

Tutto lo stato è in `~/medmonitor-data/` più il file `~/medmonitor/.env`.

```bash
systemctl --user stop medmonitor 'zigbee2mqtt*'
tar czf ~/medmonitor-backup-$(date +%F).tar.gz -C ~ medmonitor-data medmonitor/.env
systemctl --user start 'zigbee2mqtt*' medmonitor
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
| Gateway offline | `journalctl --user -u zigbee2mqtt -n 100` (gateway N: `-u zigbee2mqtt-N`); prova `timeout 3 bash -c '</dev/tcp/IP/6638'` |
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
ssh -L 8080:localhost:8080 utente@vm               # UI zigbee2mqtt dal proprio PC (gateway N: porta in Impostazioni → Gateway)
```
