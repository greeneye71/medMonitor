# Analisi di medMonitor — 8 ottobre 2026

Revisione del commit `b9d18c9`, su Windows. Esaminati backend FastAPI, SQLite, MQTT, allarmi, email, archivio, template, JavaScript e installazione Podman/Quadlet.

La suite esistente passa: **56 test, 1 avviso di deprecazione** relativo a Starlette/httpx. Dodici scenari diagnostici su database temporanei hanno riprodotto i problemi elencati sotto; due scenari riguardano lo stesso problema di freschezza dei dati. Nessuna email reale inviata. Codice applicativo e dati operativi invariati.

Priorità: **P1 alta**, da correggere prima dell'uso operativo; **P2 media**, bug funzionale o di affidabilità; **P3 bassa**, miglioramento di sicurezza nel contesto LAN previsto.

## 1. P1 — Rifiuto SMTP parziale trattato come successo completo

Riferimenti: `app/notifier.py:99`, `app/notifier.py:133`.

`send_email()` ignora il risultato di `aiosmtplib.send()`. Se il server accetta un destinatario e rifiuta un altro, la libreria restituisce gli errori per destinatario; l'eccezione per rifiuto dei destinatari viene sollevata quando sono rifiutati tutti. Il chiamante marca comunque l'intera email come inviata.

**Riproduzione:** risposta SMTP simulata con un indirizzo accettato e uno rifiutato con codice 450. Risultato: `sent=1`, `pending=0`, nessun `EMAIL_ERROR`. Il destinatario rifiutato non riceverà alcun nuovo tentativo.

**Correzione:** controllare il dizionario degli errori e conservare lo stato di consegna per destinatario, ritentando soltanto quelli rifiutati. Applicare lo stesso controllo all'email di prova.

Contratto verificato nel sorgente installato e nella [documentazione ufficiale aiosmtplib](https://aiosmtplib.readthedocs.io/en/v3.0.0/reference.html#aiosmtplib.SMTP.sendmail).

## 2. P1 — Dati vecchi acquisiscono un timestamp attuale

Riferimenti: `app/mqtt.py:93`, `app/web/admin.py:132`.

Il parser MQTT assegna `last_seen_at=now` ignorando il `last_seen` presente nel payload. Un messaggio vecchio ripubblicato o retained, quando configurato, rende online un sensore che non trasmette più. Inoltre, la tabella `discovered` conserva la temperatura senza la data dell'ultima lettura: aggiungendo un sensore viene assegnato il momento della registrazione come momento della misura.

**Riproduzione MQTT:** un payload con `last_seen` del 6 ottobre, ricevuto l'8 ottobre, viene registrato come letto l'8 ottobre; `is_offline(..., 120)` restituisce falso.

**Riproduzione registrazione:** una temperatura nella lista dei rilevati vecchia di tre giorni produce, dopo “Aggiungi”, un sensore online con `last_seen_at` appena assegnato. La soglia offline riparte e il campionamento usa il valore obsoleto.

**Correzione:** distinguere ricezione MQTT e ultima osservazione Zigbee; validare e preservare la data della lettura anche in `discovered`, senza aggiornarla durante la registrazione. Gestire messaggi fuori ordine.

Zigbee2MQTT documenta il significato di `last_seen` nelle [impostazioni ufficiali](https://www.zigbee2mqtt.io/guide/configuration/all-settings.html) e l'opzione retain nella [configurazione dei dispositivi](https://www.zigbee2mqtt.io/guide/configuration/devices-groups.html). Retain è disabilitato per default: questa specifica variante dipende dalla configurazione; il problema della registrazione è indipendente da retain.

## 3. P1 — Lo storico di un sensore rimosso restituisce un altro sensore

Riferimenti: `app/web/routes.py:123`, `app/web/routes.py:124`, `app/web/admin.py:185`.

La rimozione conserva campioni e sensore, ma `history_query()` cerca soltanto sensori attivi. Se l'identificativo richiesto manca, sceglie automaticamente il primo sensore attivo. Il comportamento riguarda anche l'esportazione CSV.

**Riproduzione:** due sensori, `0x01` e `0x02`, con temperature differenti. Rimosso `0x01`, `GET /storico.csv?sensor=0x01` risponde 200 esportando nome e campioni di `0x02`. Se non rimangono sensori attivi, lo storico appare vuoto pur essendo conservato nel DB.

**Correzione:** consentire la consultazione dei sensori disattivati. Usare un sensore predefinito soltanto quando il parametro è assente; un identificativo sconosciuto deve avere un esito esplicito.

## 4. P2 — Stato allarmi, eventi e coda email non sono atomici

Riferimenti: `app/db.py:65`, `app/monitor.py:95`, `app/monitor.py:122`.

SQLite lavora in autocommit. Evento, email e stato dell'allarme sono salvati con istruzioni separate. Un'interruzione dopo l'accodamento ma prima di `_save_state()` lascia l'email salvata e lo stato ancora chiuso; il ciclo successivo apre nuovamente lo stesso allarme.

**Riproduzione:** errore simulato nel salvataggio dello stato dopo l'apertura. Alla ripresa, una sola anomalia continua produce due eventi `TEMP_OPEN` e due email.

**Correzione:** salvare transizione, evento e outbox nella stessa transazione, proteggendo l'intera transazione con il lock della connessione condivisa. Durante lo shutdown attendere la conclusione dei job prima di chiudere il DB (`app/main.py:72` usa attualmente `wait=False`).

## 5. P2 — Un'archiviazione interrotta duplica i CSV al tentativo successivo

Riferimenti: `app/archive.py:50`, `app/archive.py:56`, `app/archive.py:58`.

I campioni vengono appesi al CSV e sincronizzati su disco prima della cancellazione dal DB. Se l'esecuzione si interrompe fra queste operazioni, la successiva archiviazione appende nuovamente gli stessi campioni. Il lock impedisce due archiviazioni contemporanee nello stesso processo, ma non risolve la ripresa dopo un errore.

**Riproduzione:** errore simulato sulla cancellazione, dopo la scrittura. Ripetendo il job, un campione originale diventa due righe identiche nel CSV.

**Correzione:** rendere l'esportazione idempotente, per esempio usando identificativi persistenti dei campioni e un protocollo di ripresa, oppure file mensili riscritti atomicamente con deduplicazione. Una sola transazione SQLite non rende atomica anche la scrittura del CSV.

## 6. P2 — Alla scadenza del silenziamento parte un allarme già rientrato

Riferimento: `app/monitor.py:65`.

Le aperture sospese vengono riaccodate prima di valutare il campione e lo stato offline attuali. Se il sensore si è ripreso proprio nel primo ciclo dopo la scadenza, vengono accodate sia l'apertura sia la chiusura.

**Riproduzione:** allarme a 12 °C durante il silenziamento; primo ciclo dopo la scadenza a 5 °C. Risultato: email “ALLARME TEMPERATURA — 5,0 °C” seguita immediatamente da “TEMPERATURA RIENTRATA”.

**Correzione:** rivalutare gli allarmi prima della riaccodatura e notificare soltanto quelli ancora aperti, evitando una seconda apertura quando il ciclo ha già prodotto la transizione.

## 7. P2 — Sensori con nome MQTT contenente `/` ignorati

Riferimenti: `app/mqtt.py:74`, `app/mqtt.py:130`.

Zigbee2MQTT supporta nomi come `farmacia/frigo`. La sottoscrizione `zigbee2mqtt/+` copre soltanto un livello; inoltre il parser scarta ogni sottotopic che contiene `/`.

**Riproduzione:** dispositivo correttamente mappato a `farmacia/frigo`; un messaggio con temperatura 9 °C lascia la temperatura precedente a 4 °C. Il dispositivo può comparire fra i rilevati ma non ricevere aggiornamenti nell'app.

**Correzione:** sottoscrivere i topic completi dei dispositivi o usare una sottoscrizione gerarchica con riconoscimento esatto dei nomi; distinguere esplicitamente messaggi dispositivo e topic di comando/availability.

Supporto ai nomi gerarchici verificato nella [documentazione ufficiale Zigbee2MQTT](https://www.zigbee2mqtt.io/guide/configuration/devices-groups.html).

## 8. P2 — `NaN` supera la validazione delle soglie

Riferimento: `app/web/admin.py:52`.

`float('nan')` è accettato e tutti i confronti di ordinamento/range con NaN sono falsi. La validazione restituisce quindi soglie considerate valide.

**Riproduzione:** `min_c=nan` nella modifica di un sensore produce HTTP 500, perché sqlite3 converte NaN in NULL e viola `NOT NULL`. Nel salvataggio dei preset il valore viene persistito nel JSON delle impostazioni, compromettendo le soglie proposte.

**Correzione:** verificare `math.isfinite()` su entrambi i valori prima dei confronti; rifiutare valori non finiti anche nella serializzazione delle impostazioni.

## 9. P2 — SMTP non configurato lascia notifiche ferme senza avviso globale

Riferimenti: `app/notifier.py:114`, `app/web/routes.py:92`.

Con host SMTP vuoto o nessun destinatario il job ritorna immediatamente. Le email restano pendenti con zero tentativi; il contatore degli errori resta a zero e il banner non segnala l'impossibilità di inviare notifiche.

**Riproduzione:** sensore online, temperatura regolare e batteria bassa, con SMTP non configurato. Email di batteria in coda, zero tentativi; la panoramica mostra “Tutto regolare”. Il dettaglio della batteria è presente sulla scheda, ma manca l'avviso sulla consegna delle notifiche.

**Correzione:** mostrare esplicitamente lo stato della configurazione email e le notifiche bloccate. Distinguere assenza di configurazione, invio in corso ed errori SMTP.

## 10. P2 — Il controllo finale dell'installer accetta servizi non operativi

Riferimenti: `app/main.py:104`, `install.sh:226`.

`/health` restituisce 200 anche quando MQTT o scheduler sono fermi. L'installer considera il solo successo di `curl -fs` come installazione completata, senza controllare i valori JSON. Un'app HTTP funzionante con broker/gateway irraggiungibile supera quindi il controllo finale.

**Verifica locale:** con servizi disabilitati, risposta 200 e `mqtt_connected=false`, `gateway_online=false`, `scheduler_running=false`. Il comportamento dell'installer è confermato dalla lettura dello script; la procedura completa Fedora non è stata eseguita.

**Correzione:** distinguere vitalità del processo e prontezza operativa, oppure verificare nel JSON almeno DB, scheduler e connessione MQTT, riportando esplicitamente lo stato del gateway.

## 11. P3 — Il cambio password mantiene valide le sessioni precedenti

Riferimenti: `app/web/admin.py:436`, `app/auth.py:32`.

Il cookie contiene il solo flag `admin`; il controllo di accesso non verifica una versione della password o della sessione. Cambiare password non revoca l'accesso dei browser già autenticati, che possono continuare a modificare le impostazioni finché la sessione rimane valida.

**Riproduzione:** due client autenticati. Dopo il cambio password dal primo, il secondo accede ancora alle impostazioni con HTTP 200.

**Correzione:** associare alle sessioni una versione persistita e incrementarla al cambio password, mantenendo o rinnovando esplicitamente la sessione dell'utente che effettua il cambio.

## Osservazione sul campionamento previsto dalla specifica

`app/monitor.py:20` ricopia ogni dieci minuti l'ultima temperatura finché non scatta la soglia offline: con il default di 120 minuti si possono registrare molti campioni dallo stesso messaggio. È il comportamento esplicitamente previsto dalla specifica attuale, quindi non è conteggiato come ulteriore bug. Per interpretare correttamente grafici, statistiche e “N campioni consecutivi”, conviene conservare anche il timestamp della lettura originale e indicare se il campione riutilizza un valore precedente.

## Verifiche e limiti

- Suite: `.venv2\Scripts\python.exe -m pytest -q` → 56 passati.
- Riproduzioni: script diagnostico locale `.pytest_cache/audit_repro.py`, con asserzioni sui comportamenti attuali, database temporanei e SMTP simulato. Include errori iniettati per verificare il recupero dopo interruzioni.
- Verificati login, pagine e CSV attraverso `TestClient`, senza servizi reali.
- Restano da verificare sul sistema Fedora: installazione completa, rete Podman, riavvio effettivo Zigbee2MQTT, sensori fisici e consegna SMTP reale. Il rendering del browser non è stato ispezionato visivamente.
- La modifica preesistente a `.claude/settings.local.json` è stata preservata.
