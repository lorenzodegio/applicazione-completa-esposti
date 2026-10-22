# Diario delle decisioni

Decisioni prese strada facendo, senza un confronto preventivo: data, cosa, perché.
Le decisioni di prodotto stabili finiscono anche in `backend/api/README.md` («Decisioni»).

## 2026-10-21 — ambiente Docker, salute, temi, versione della valutazione (Agente A, ramo `lorenzo`)

- **Compose con progetto `esposti-app`** nella radice; immagini costruite dai Dockerfile del repository
  (`backend/Dockerfile` unica per api, worker, finto motore e test; `frontend/backoffice/Dockerfile`;
  `e2e/Dockerfile`). Motivo: dipendenze installate una volta in build, avvio veloce, nessun `pip`/`npm` all'avvio.
- **Sorgenti del backend dentro l'immagine** (si ricostruisce con `--build`), **`src/` del backoffice montata**
  in sola lettura. Motivo: il backend deve essere riproducibile nelle prove; il frontend beneficia del
  ricaricamento al volo di Vite.
- **Container senza privilegi** (utente `esposti` uid 1000 nel backend, `node` nel backoffice). Motivo: igiene minima.
- **Database di sviluppo su volume `pgdata`**, **archivio su volume `archivio`**; `down -v` azzera entrambi.
  Un database `esposti_test` separato (creato da `docker/db/initdb.sql`) per pytest. Motivo: i test non
  devono mai toccare i dati dell'ambiente di sviluppo.
- **Healthcheck di PostgreSQL su `-h 127.0.0.1`**. Motivo: durante l'inizializzazione il server temporaneo
  ascolta solo sul socket; così il servizio risulta pronto solo dopo `initdb.sql`.
- **Reti**: `worker` **e `api`** su `default` + `esposti_interna` (esterna, interna senza internet);
  `motore-finto` solo su `default`. Motivo: `api` deve poter interrogare il motore vero per `/salute`;
  il finto non va sulla rete condivisa per non creare ambiguità di nomi con altri progetti.
- **`MOTORE_URL` → `ESPOSTI_MOTORE_URL`** di api e worker, default `http://motore-finto:8080`.
- **La demo usa sempre il finto nello stesso processo**, anche con il motore vero. Motivo: i suoi file sono
  sintetici e costruiti per gli scenari del finto; inviarli al motore vero darebbe risultati senza senso.
- **Finto motore**: `python -m motore.finto` legge `MOTORE_FINTO_HOST` (default `0.0.0.0`, adatto a Docker)
  e `MOTORE_FINTO_PORTA` (default 8080).
- **Worker**: crea la cartella temporanea se manca; all'avvio cancella le cartelle `esposti-*` rimaste da
  un'interruzione. Motivo: un documento non deve restare sulla macchina dopo un arresto brusco.
- **`/salute`**: 503 solo per database o archivio non funzionanti; motore irraggiungibile o contratto di
  versione principale diversa = `degradato` con 200. Motivo: senza motore le persone lavorano comunque
  e i lavori aspettano in coda; un 503 farebbe anche fallire l'healthcheck e bloccare lo stack quando il
  motore vero non c'è. Timeout verso il motore: 2 s. Nessun URL o messaggio interno nella risposta.
- **Compatibilità del contratto** in `/salute`: stessa versione principale (`1.x`). Motivo: le versioni
  minori del contratto aggiungono, non rompono (da confermare quando il contratto passerà a 2.0).
- **Archivio: nuovo metodo `verifica()`** nell'interfaccia (scrive e cancella un file di prova). Motivo:
  `/salute` non deve conoscere l'implementazione; SharePoint dovrà implementarlo a sua volta.
- **Temi non toccati accettati** (decisione del coordinatore): il backend li conferma a nome di chi valida
  e lo scrive nel registro con `implicito: true`. Il backoffice continua a inviare tutte le decisioni
  (i temi proposti partono già su «Conferma»: si invia ciò che si vede) e lo dice con una riga nel modulo.
- **Versione della valutazione** (decisione del coordinatore): campo `versione` nel corpo, `null` = «non
  c'era ancora». Anche una creazione concorrente (due persone che partono entrambe da nessuna valutazione)
  dà 409. Il 409 ha `codice: "valutazione_modificata"` per distinguerlo dagli altri conflitti; il backoffice
  ricarica la pratica, riparte dalla valutazione salvata da altri e avvisa. La versione della pratica
  (`pratica.versione`) resta separata e non cambia con il salvataggio di una bozza.
- **Decisioni «da confermare» del README del backend**: tutte confermate così come erano (restituzione,
  limite di accesso, amministratore, IN_ANALISI → DA_SMISTARE, ritentativi, registro delle letture,
  attività, «senza riscontro», collegamenti, chi crea le pratiche). Motivo: coerenti con il piano e coperte
  da test; nessun caso d'uso visto finora le contraddice.
- **Prove in progetti compose separati** (`esposti-prove-<suite>`), database su tmpfs, nessuna porta
  sull'host, sempre il finto, `down -v` prima e dopo. Motivo: «database pulito a ogni esecuzione» e
  nessun conflitto con lo stack di sviluppo acceso. Un solo comando: `scripts/prove.sh`.
- **End-to-end con Playwright 1.63.0** (immagine `mcr.microsoft.com/playwright:v1.63.0-noble`), Chromium.
  Motivo: versione stabile di settembre 2026, non l'ultimissima. Il browser raggiunge il backoffice come
  `http://backoffice:5173`: per questo Vite accetta l'host da `VITE_HOST_AMMESSI`.
- **Scenari del finto: sono 9, non 8** (lettura pulita, riscontro, manoscritto/incerto, formato/.pages,
  illeggibile, scaduto, instabile, occupato, invalido): l'end-to-end li copre tutti.
- **Intervallo del worker 0,5 s nelle prove** (2 s in sviluppo). Motivo: prove più rapide, stessa logica.

## 2026-10-21 — correzioni dopo la revisione (Agente A, ramo `lorenzo`)

- **Timeout dell'applicazione 2100 s** (era 600). Motivo: il motore vero ha `tempo_max_s = 1800`
  (circa 45 s per pagina trascritta); con un'attesa più lunga è il motore a dichiarare `tempo_scaduto`
  e l'applicazione non abbandona un lavoro che sta ancora andando.
- **Codici HTTP in `stato()` del client**: il corpo conta più del codice. Corpo conforme = si usa
  (anche il 404 del motore riavviato, `errore_interno` ritentabile); corpo non conforme con codice ≠ 200 =
  `MotoreIrraggiungibile`, ritentabile; corpo non conforme con 200 = `risultato_non_valido`. Motivo: un
  500 o un URL sbagliato non sono un risultato fuori contratto e non devono bloccare per sempre il documento.
- **`/salute` con motore «non_pronto»**: motore raggiungibile ma con `stato` diverso da `pronto` →
  motore `non_pronto`, generale `degradato` (200). Motivo: il motore vero dice `non_pronto` se manca il
  modello o i digest non coincidono; i lavori non andrebbero avanti.
- **Contratto 1.2** (versione minore): `richiesta_non_valida` (422, non ritentabile), anche nel finto;
  annotati `acquisizione` sempre `ocr` nel motore vero, `frase` convenzionale del protocollo dal nome del
  file, `.eml` non supportato. `Risultato.versione_contratto` deve essere `1.x` (qualunque minore). Motivo:
  allineare il contratto a ciò che il motore vero fa davvero; la regola delle versioni minori lo consente.
- **Protocollo: numero + anno**, con una colonna calcolata dal database (`chiave_protocollo`, migrazione
  0006) invece che in Python. Motivo: il protocollo si scrive in più punti (creazione, modifica, worker); una
  colonna generata è sempre coerente e indicizzabile. Spazi intorno alla barra e maiuscole non contano;
  gli zeri iniziali sì (non si sa se `12` e `0000012` siano lo stesso protocollo).
- **Temporanei del worker su tmpfs** (`/tmp/esposti-lavoro`, 1 GB): il documento scaricato non tocca mai
  il disco del container, come nel motore.

## 2026-10-21 — aggancio con il motore vero (coordinatore)

- **Prova di aggancio separata da `scripts/prove.sh`** (`scripts/prova-motore-vero.sh`,
  `compose.motore-vero.yml`, `e2e/motore-vero/`). Motivo: usa la GPU e dura minuti; le prove normali
  restano veloci e sempre con il finto.
- **Documenti della prova: quelli sintetici del motore**, montati in sola lettura nel solo container
  Playwright, con gli stessi nomi dichiarati della prova del motore. Motivo: sono fatti per il motore vero
  (scansioni, scrittura a mano); non si copiano qui per non duplicare file del motore. Nessuna cartella di
  lavoro del motore è montata.
- **Controlli sui temi**: ogni tema proposto deve stare nel vocabolario e avere la frase; si richiede che
  almeno un documento ne abbia, non tutti. Motivo: un documento può legittimamente non riguardare nessun
  tema (per esempio un riscontro generico); la qualità dei temi la giudica Lorenzo.

## 2026-10-22 — caricamento dal backoffice e ripartenza da zero (coordinatore)

- **Caricamento in Smistamento rifatto** (`componenti/CaricaDocumenti.tsx`): solo PDF, Word e RTF
  (rifiuto prima dell'invio); con più file, una pratica per file (predefinito) o tutte in una;
  invio un file alla volta con avanzamento (XMLHttpRequest, perché fetch non espone l'avanzamento
  del caricamento); stato dell'analisi di ogni documento da `GET /lavori/{id}` ogni 3 s finché il
  lavoro non è completato o in errore. Motivo: le prove con molti documenti propri, uno per pratica.
- **Formato non supportato nell'end-to-end**: il modulo ora rifiuta `.pages`; la prova verifica il
  rifiuto e crea quella pratica dall'API, così il percorso d'errore del motore resta coperto.
- **`python -m api.azzera`**: un unico TRUNCATE delle 12 tabelle legate alle pratiche (si riferiscono
  l'una all'altra), trigger del registro disattivati e riattivati nella stessa transazione, prima riga
  del registro nuovo `sistema.azzera`; numerazione da 1; archivio svuotato (radici sospette rifiutate).
  Restano anche le sessioni, perché gli utenti restano. Il test lavora in una transazione annullata e
  non riavvia la numerazione, per non toccare i dati degli altri test.
- **`DEMO=0`** nel compose: senza, all'avvio `api` ricreerebbe le pratiche demo dopo lo svuotamento.
