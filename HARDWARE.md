# Hardware

## Gateway Zigbee: SONOFF Dongle-M

Coordinatore Zigbee con porta Ethernet: si collega alla rete, non alla VM, quindi
nessun passthrough USB.

- Firmware coordinatore **EZSP/Ember**, server TCP sulla porta **6638** (impostazione di fabbrica).
- In zigbee2mqtt: `port: tcp://IP:6638`, `adapter: ember` (lo scrive `install.sh`).
- Deve avere un **IP fisso**: prenotazione DHCP sul router (consigliato) o IP statico
  dalla pagina web del dongle. Vedi [INSTALL.md](INSTALL.md), passo 2.
- Posizionalo in un punto centrale rispetto ai frigoriferi: le pareti metalliche
  dei frigoriferi attenuano molto il segnale Zigbee.
- **Un Dongle-M per ambiente**: un gateway copre un'area limitata, quindi ogni ambiente
  lontano dagli altri ha il suo, collegato alla rete Ethernet, con il suo **IP fisso** e la sua
  rete Zigbee. Tutti nella stessa LAN della VM; pensato per 1–6 gateway.
  Si aggiungono con `./install.sh` ([INSTALL.md](INSTALL.md), "Aggiungere un ambiente").

## Sensori: SONOFF SNZB-02LD

Sensore di temperatura Zigbee con sonda esterna a cavo e display.

- La sonda va dentro il frigorifero o il congelatore, il corpo con display e batteria resta fuori:
  il cavo passa dalla guarnizione della porta e la batteria non lavora al freddo.
- Riportano anche il livello di batteria, usato per l'allarme "batteria scarica".
- Abbinamento: tieni premuto il pulsante finché il LED lampeggia (circa 5 s)
  con la finestra di abbinamento aperta in medMonitor.

Altri sensori di temperatura supportati da zigbee2mqtt funzionano se pubblicano
il campo `temperature` (e opzionalmente `battery`), ma sono stati provati solo gli SNZB-02LD.
Previsti in futuro: **SNZB-02M** e **SNZB-02UL**, da verificare quando disponibili.

## VM Fedora

| Risorsa | Minimo |
|---|---|
| Sistema | Fedora 39 o successiva, utente non root con `sudo` |
| CPU | 1 vCPU (2 consigliate) |
| RAM | 2 GB |
| Disco | 10 GB liberi |
| Rete | stessa LAN dei Dongle-M (TCP 6638 raggiungibile), SMTP in uscita |

Spazio: il database tiene solo gli ultimi 180 giorni (modificabile), il resto va
nell'archivio CSV, che cresce di circa 200 KB al mese per sensore.

Server di posta: qualunque SMTP con STARTTLS (587), SSL/TLS (465) o relay interno (25).
