# Manuale utente — medMonitor

Questa guida spiega come usare medMonitor per monitorare le temperature
dei frigoriferi e freezer e gestire gli allarmi.

---

## Indice

1. [Panoramica](#1-panoramica)
2. [Accesso alla dashboard](#2-accesso-alla-dashboard)
3. [Dashboard — Monitoraggio in tempo reale](#3-dashboard)
4. [Storico — Analisi temperature](#4-storico)
5. [Allarmi — Gestione notifiche](#5-allarmi)
6. [Impostazioni](#6-impostazioni)
7. [Gestione allarmi via email](#7-gestione-allarmi-via-email)
8. [Modalita demo](#8-modalita-demo)
9. [Operazioni quotidiane](#9-operazioni-quotidiane)
10. [Domande frequenti](#10-domande-frequenti)

---

## 1. Panoramica

medMonitor e un sistema di monitoraggio della temperatura per celle frigorifere e freezer.
Raccoglie automaticamente i dati dai sensori wireless ZigBee e:

- Mostra le temperature in tempo reale su una dashboard web
- Invia email di allarme quando una temperatura esce dai limiti
- Conserva lo storico delle temperature per analisi e audit
- Permette di configurare soglie diverse per ogni sensore

### Come funziona

```
Sensori ZigBee  -->  Gateway Wi-Fi  -->  medMonitor  -->  Dashboard + Email
   (nei frigo)       (nella rete)        (sul PC)         (nel browser)
```

I sensori misurano la temperatura ogni 10 minuti. medMonitor controlla i valori
e se una temperatura resta fuori soglia per piu di 15 minuti, invia un allarme.

## 2. Accesso alla dashboard

Apri il browser e vai su:

**http://localhost:8050**

Se accedi da un altro PC nella stessa rete, sostituisci `localhost` con l'indirizzo IP
del computer dove gira medMonitor (es. `http://192.168.1.50:8050`).

La dashboard ha 4 sezioni accessibili dalla barra laterale sinistra:

| Sezione | Descrizione |
|---|---|
| **Dashboard** | Vista in tempo reale di temperature, sensori, allarmi |
| **Storico** | Grafici storici, statistiche, esportazione CSV |
| **Allarmi** | Tabella di tutti gli allarmi con filtri |
| **Impostazioni** | Configurazione completa del sistema |

## 3. Dashboard

La pagina Dashboard e il pannello principale di monitoraggio.

### 3.1 Schede riassuntive (in alto)

Quattro schede mostrano lo stato attuale:

| Scheda | Cosa mostra |
|---|---|
| **Frigorifero** | Temperatura attuale del frigorifero |
| **Freezer** | Temperatura attuale del freezer |
| **Allarmi attivi** | Numero di allarmi critici in corso |
| **Sensori online** | Numero di sensori che trasmettono dati |

### 3.2 Schede zona (al centro)

Per ogni zona (frigorifero e freezer) viene mostrata una scheda con:

- **Stato**: OK (verde), AVVISO (giallo), ALLARME (rosso)
- **Temperatura attuale**: il valore letto dal sensore
- **Barra indicatore**: mostra visivamente la posizione della temperatura rispetto ai limiti
- **Soglie**: i limiti min e max configurati
- **Stella** (se presente): indica che il sensore ha soglie personalizzate diverse da quelle di zona

**Significato dei colori:**

| Colore | Stato | Significato |
|---|---|---|
| Verde (#1D9E75) | OK | Temperatura nella norma |
| Giallo (#BA7517) | WARNING | Fuori soglia da meno di 15 minuti |
| Rosso (#E24B4A) | CRITICAL | Fuori soglia da piu di 15 minuti |

### 3.3 Grafico ultime 24 ore

Il grafico mostra l'andamento della temperatura nelle ultime 24 ore per tutti i sensori.

- Ogni sensore ha una linea di colore diverso
- Le **bande colorate trasparenti** indicano le soglie consentite
- Puoi **zoomare** trascinando il mouse su un'area del grafico
- Puoi **spostare** il grafico tenendo premuto Shift e trascinando
- Fai **doppio clic** per tornare alla vista completa

### 3.4 Tabella sensori

In fondo alla pagina, una tabella elenca tutti i sensori con:

- Indicatore di stato (pallino colorato)
- ID del sensore
- Zona (fridge/freezer)
- Temperatura attuale
- Livello batteria
- Data/ora dell'ultima lettura

### 3.5 Aggiornamento automatico

La dashboard si aggiorna automaticamente **ogni 30 secondi**. Non serve ricaricare la pagina.

## 4. Storico

La pagina Storico permette di analizzare i dati passati.

### 4.1 Filtri

- **Periodo**: seleziona data inizio e fine con il calendario
- **Zona**: filtra per "Frigorifero", "Freezer" o "Tutte"
- **Sensori**: seleziona uno o piu sensori specifici
- Clicca **"Cerca"** per caricare i dati

### 4.2 Grafico interattivo

Il grafico mostra le temperature nel periodo selezionato con:
- Zoom e pan con il mouse
- Tooltip con valori precisi passando sopra le linee
- Bande soglia per ogni sensore

### 4.3 Statistiche

Sotto il grafico vengono mostrate le statistiche del periodo:

| Statistica | Descrizione |
|---|---|
| **Media** | Temperatura media nel periodo |
| **Min** | Temperatura minima registrata |
| **Max** | Temperatura massima registrata |
| **Letture** | Numero totale di misurazioni |

### 4.4 Esportazione CSV

Clicca **"Esporta CSV"** per scaricare i dati in formato CSV.
Il file contiene: data/ora, zona, sensore, temperatura, umidita, batteria.

Puoi aprirlo con Excel, LibreOffice Calc, o qualsiasi software di analisi dati.

## 5. Allarmi

La pagina Allarmi mostra lo storico completo di tutti gli allarmi generati.

### 5.1 Filtri

- **Zona**: filtra per frigorifero o freezer
- **Livello**: filtra per WARNING o CRITICAL
- **Periodo**: seleziona un intervallo di date

### 5.2 Tabella allarmi

La tabella usa **AG Grid** con funzionalita avanzate:

- **Ordinamento**: clicca sull'intestazione di una colonna per ordinare
- **Filtro rapido**: clicca sull'icona filtro nell'intestazione per filtrare i valori
- **Ridimensionamento**: trascina il bordo delle colonne per ridimensionarle
- **Paginazione**: 20 allarmi per pagina, naviga con i pulsanti in basso

### 5.3 Colonne

| Colonna | Descrizione |
|---|---|
| Data/Ora | Quando si e verificato l'allarme |
| Zona | Frigorifero o freezer |
| Sensore | ID del sensore coinvolto |
| Temp (°C) | Temperatura al momento dell'allarme |
| Livello | WARNING (giallo) o CRITICAL (rosso) |
| Messaggio | Descrizione dell'allarme |

### 5.4 Contatore nella barra di navigazione

Il badge nella barra in alto mostra sempre il numero di allarmi attivi:
- **Verde "0 allarmi"**: tutto nella norma
- **Giallo**: ci sono avvisi (WARNING)
- **Rosso**: ci sono allarmi critici (CRITICAL)

## 6. Impostazioni

La pagina Impostazioni ha 7 tab per configurare ogni aspetto del sistema.

### 6.1 Generale

- **Nome impianto**: nome visualizzato nella dashboard
- **Tema UI**: scegli tra 4 temi grafici (SLATE scuro, VAPOR viola, FLATLY chiaro, COSMO minimal)
- **Log level**: livello di dettaglio dei log (INFO per uso normale, DEBUG per diagnostica)

### 6.2 Soglie temperatura

Qui si configurano i limiti di temperatura che generano allarmi.

**Default di zona:**
Due cursori (slider) per impostare il range accettabile per ogni zona:
- Frigorifero: default 0°C — 30°C
- Freezer: default -30°C — 0°C

**Soglie per sensore:**
Ogni sensore puo avere soglie diverse da quelle di zona.
- Attiva l'interruttore "override" per un sensore
- Imposta min e max personalizzati
- Il sensore con soglie individuali mostra una stella nella dashboard

**Esempio pratico:**
Un frigorifero farmaceutico potrebbe avere soglie piu strette (2°C — 8°C)
rispetto al default di zona (0°C — 30°C).

### 6.3 Sensori

Tabella modificabile dei sensori registrati:
- **Nome**: assegna un nome descrittivo (es. "Frigo Sala A")
- **Zona**: assegna a fridge o freezer
- **Attivo**: disattiva un sensore senza eliminarlo

### 6.4 Email

Configurazione completa per invio (SMTP) e ricezione (IMAP).

**SMTP — Invio allarmi:**
- Host, porta, TLS, credenziali
- Lista destinatari (separati da virgola)
- Pulsante **"Test SMTP"**: invia un'email di prova

**IMAP — Ricezione conferme (opzionale):**
- Host, porta, SSL, credenziali
- Cartella da monitorare
- Intervallo di controllo
- Pulsante **"Test IMAP"**: verifica la connessione

Il badge verde "OK" conferma che la configurazione funziona.

### 6.5 Database

- **TinyFlux**: database file locale, ideale per piccole installazioni (2-5 sensori)
- **TimescaleDB**: database PostgreSQL, per installazioni piu grandi (10+ sensori)

Il pulsante "Migra dati" trasferisce lo storico da TinyFlux a TimescaleDB.

### 6.6 Sistema

- **Intervallo polling**: ogni quanti minuti leggere i sensori (default 10 min)
- **Cooldown allarmi**: tempo minimo tra email successive per lo stesso sensore (default 30 min)
- **Retention dati**: per quanti giorni conservare lo storico (default 365 giorni)
- **Backup**: esporta e importa la configurazione completa

### 6.7 Demo

Avvia la modalita demo per testare il sistema senza sensori reali.
Vedi la sezione [Modalita demo](#8-modalita-demo) per i dettagli.

## 7. Gestione allarmi via email

### 7.1 Come funzionano gli allarmi

1. Un sensore rileva una temperatura fuori soglia
2. Se resta fuori soglia per **meno di 15 minuti** → allarme **WARNING**
3. Se resta fuori soglia per **piu di 15 minuti** → allarme **CRITICAL**
4. medMonitor invia un'email a tutti i destinatari configurati
5. Dopo l'invio, attende il **cooldown** (default 30 min) prima di inviare un altro allarme per lo stesso sensore

### 7.2 Email di allarme

Le email hanno un formato chiaro con:
- Intestazione colorata (giallo per WARNING, rosso per CRITICAL)
- Temperatura attuale e soglie consentite
- Dettagli del sensore e della zona
- Istruzioni per rispondere

### 7.3 Rispondere agli allarmi (richiede IMAP)

Se hai configurato IMAP, puoi rispondere direttamente alle email di allarme con questi comandi:

| Comando | Cosa fa |
|---|---|
| **ACK** | Conferma che hai preso in carico l'allarme |
| **MUTE 2h** | Silenzia gli allarmi per 2 ore (utile durante manutenzione) |
| **ESCALATE** | Inoltra l'allarme al livello superiore |
| **STATUS** | Richiedi lo stato attuale di tutti i sensori via email |

Per usarli: rispondi all'email scrivendo **solo il comando nella prima riga**.

**Esempio:** ricevi un allarme per il freezer. Rispondi con:
```
ACK
```
L'allarme verra segnato come "confermato" nella dashboard.

## 8. Modalita demo

La modalita demo genera dati simulati realistici per:
- Testare la dashboard prima di collegare sensori reali
- Verificare che gli allarmi email funzionino
- Fare dimostrazioni del sistema

### 8.1 Scenari disponibili

| Scenario | Durata simulata | Cosa simula |
|---|---|---|
| **Normale** | 24 ore | Temperature stabili, nessun allarme |
| **Allarme frigo** | 24 ore | Porta del frigorifero aperta, temperatura sale |
| **Allarme freezer** | 24 ore | Guasto termostato, temperatura scende |
| **Blackout** | 24 ore | Interruzione corrente, entrambe le zone salgono |
| **Batteria scarica** | 24 ore | Un sensore esaurisce la batteria e va offline |
| **Stress test** | 48 ore | Tutti gli scenari in sequenza (consigliato per primo test) |

### 8.2 Velocita di simulazione

| Velocita | Quanto dura | Consigliato per |
|---|---|---|
| 1x | Tempo reale | Monitoraggio prolungato |
| **10x** | ~2 min per 24h simulate | **Prima demo** |
| 60x | ~20 sec per 24h | Test rapido |
| 600x | ~2 sec per 24h | Stress test |

### 8.3 Come avviare la demo

1. Vai su **Impostazioni** > tab **Demo**
2. Seleziona uno scenario (consigliato: **Stress test**)
3. Seleziona la velocita (consigliato: **10x**)
4. Clicca **"Avvia demo"**
5. Torna alla **Dashboard** per vedere i dati simulati

Un banner giallo in cima a tutte le pagine indica che la demo e attiva.

### 8.4 Fermare e pulire

- **"Ferma demo"**: interrompe la generazione di dati
- **"Reset dati demo"**: cancella tutti i dati simulati (quelli con prefisso `0xDEMO`)
  senza toccare i dati reali dei sensori

## 9. Operazioni quotidiane

### 9.1 Routine giornaliera

1. Controlla la **Dashboard** per verificare che tutti i sensori siano online
2. Verifica il badge allarmi nella barra in alto (deve essere verde)
3. Se ci sono allarmi, controlla la pagina **Allarmi** per i dettagli

### 9.2 Routine settimanale

1. Vai su **Storico** e seleziona l'ultima settimana
2. Verifica che non ci siano anomalie ricorrenti
3. Esporta il CSV se necessario per documentazione/audit

### 9.3 Routine mensile

1. Verifica il livello batteria dei sensori nella tabella della Dashboard
2. Sostituisci le batterie sotto il 20%
3. Esegui un backup dei dati (vedi sezione backup nella guida installazione)

### 9.4 Avvio e arresto del sistema

**Avvio**: doppio clic su `start.bat` oppure avvia manualmente i due terminali.

**Arresto**: chiudi le due finestre di terminale (Backend e Frontend).

Il servizio Mosquitto resta sempre attivo come servizio Windows.

## 10. Domande frequenti

### Quanti sensori posso collegare?
Con TinyFlux (default): fino a 5-10 sensori. Con TimescaleDB: centinaia.

### I dati vengono persi se spengo il PC?
No. I dati sono salvati su disco (file `data/temperature.db` per TinyFlux).
Al riavvio ripartono dall'ultimo punto salvato.

### Posso accedere alla dashboard da telefono?
Si. La dashboard e responsiva. Apri il browser del telefono e vai su
`http://IP_DEL_PC:8050` (devi essere sulla stessa rete Wi-Fi).

### Posso monitorare piu sedi?
Con una singola installazione puoi monitorare una sede.
Per piu sedi, installa medMonitor su ogni sede oppure valuta
la migrazione a TimescaleDB con accesso remoto.

### Ogni quanto vengono letti i sensori?
Ogni 10 minuti (configurabile in Impostazioni > Sistema > Intervallo polling).

### Quanto spazio disco serve?
Con 2 sensori a 10 minuti, TinyFlux usa circa 50 MB/anno.
Con TimescaleDB lo spazio e simile ma con compressione automatica.

### Posso cambiare la lingua?
L'interfaccia e in italiano. I termini tecnici (fridge/freezer nei dati)
sono in inglese per compatibilita con Zigbee2MQTT.

### Come faccio a sapere se un sensore e offline?
Nella tabella sensori della Dashboard, controlla la colonna "Ultimo aggiornamento".
Se la data e vecchia di piu di 20 minuti, il sensore potrebbe essere offline o avere la batteria scarica.

---

*Documentazione medMonitor — Ultimo aggiornamento: marzo 2026*
