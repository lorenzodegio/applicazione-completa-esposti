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
