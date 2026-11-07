# backend/api

Server applicativo del backoffice: **FastAPI + PostgreSQL** (SQLAlchemy 2, Alembic).
Piano di riferimento: [docs/piano.md](../../docs/piano.md) (sezioni 3, 6, 7).

## Stato

Fase 1 (server di base), 2 (motore finto) e 3–4 (backend dell'operatore) **fatte**:

- accesso, ruoli, permessi (filtro unico `pratiche_visibili`, 404 fuori perimetro, ripetuto
  in test a livello di funzione), registro di sola aggiunta;
- caricamento a mano, archivio locale, coda e worker, risultati del motore, rilancio;
- **valutazione** dell'operatore (distinta dalla proposta dell'IA; la precompilazione si calcola e
  non si salva), **validazione** (`DA_VALIDARE → IN_LAVORAZIONE`, atomica), **temi** (proposti dall'IA
  dal documento principale, confermati/scartati/aggiunti dall'operatore), **attività**;
- **disaccordo IA–operatore** come vista SQL (`pratica_disaccordo`): un'unica definizione per elenco,
  dettaglio e Home; **collegamenti** (automatici per protocollo + manuali con tipo, rimozione logica,
  pratiche altrui con solo numero/ufficio/stato), **percorso** calcolato, **fascicoli**, **Home**,
  ricerca rapida, vocabolari/temi/tipi in sola lettura;
- filtri di Gestione pratiche: testo, stato, tema, tipo, valutazione ATS, disaccordo, lettura incerta, date.

Da fare: importazione del CSV ATS (fase 5) e da cartella, ufficio suggerito (serve la tabella
ambito → ufficio), SharePoint, riassegnazione/gestione utenti oltre al minimo, esportazioni.

## Avvio in sviluppo

Il modo raccomandato è Docker Compose dalla radice del repository (dettagli in
[docs/avvio.md](../../docs/avvio.md)):

```
docker compose up -d --build        # db, api (migrazioni + demo), worker, motore-finto, backoffice
curl -s http://127.0.0.1:8100/api/v1/salute
```

L'immagine `backend/Dockerfile` contiene dipendenze e sorgenti (api, worker, finto motore, test).
Senza Docker resta possibile il percorso classico (`pip install -e ".[dev]"`, `alembic upgrade head`,
`python -m api.seed`, `uvicorn api.main:app`), con `PYTHONPATH=..`.

## API (`/api/v1`)

Documentazione interattiva su `/docs` quando il server gira.

| Endpoint | Gruppo |
|---|---|
| `POST /auth/login` | accesso |
| `POST /auth/logout` | accesso |
| `GET /auth/me` | accesso |
| `GET /uffici` | amministrazione |
| `POST /uffici` | amministrazione |
| `PATCH /uffici/{ufficio_id}` | amministrazione |
| `GET /utenti` | amministrazione |
| `POST /utenti` | amministrazione |
| `PATCH /utenti/{utente_id}` | amministrazione |
| `POST /utenti/{utente_id}/password` | amministrazione |
| `DELETE /collegamenti/{collegamento_id}` | collegamenti |
| `GET /pratiche/ricerca-rapida` | collegamenti |
| `GET /pratiche/{pratica_id}/collegamenti` | collegamenti |
| `POST /pratiche/{pratica_id}/collegamenti` | collegamenti |
| `GET /pratiche/{pratica_id}/percorso` | collegamenti |
| `GET /documenti/{documento_id}/analisi` | documenti e motore |
| `POST /documenti/{documento_id}/analisi` | documenti e motore |
| `GET /documenti/{documento_id}/contenuto` | documenti e motore |
| `GET /documenti/{documento_id}/testo` | documenti e motore |
| `GET /lavori/{lavoro_id}` | documenti e motore |
| `POST /pratiche` | documenti e motore |
| `GET /pratiche/{pratica_id}/documenti` | documenti e motore |
| `POST /pratiche/{pratica_id}/documenti` | documenti e motore |
| `PATCH /attivita/{attivita_id}` | operatore |
| `GET /pratiche/{pratica_id}/attivita` | operatore |
| `POST /pratiche/{pratica_id}/attivita` | operatore |
| `GET /pratiche/{pratica_id}/temi` | operatore |
| `PUT /pratiche/{pratica_id}/temi` | operatore |
| `POST /pratiche/{pratica_id}/validazione` | operatore |
| `GET /pratiche/{pratica_id}/valutazione` | operatore |
| `PUT /pratiche/{pratica_id}/valutazione` | operatore |
| `GET /inbox` | pratiche |
| `GET /pratiche` | pratiche |
| `GET /pratiche/{pratica_id}` | pratiche |
| `PATCH /pratiche/{pratica_id}` | pratiche |
| `POST /pratiche/{pratica_id}/assegnazione` | pratiche |
| `GET /pratiche/{pratica_id}/note` | pratiche |
| `POST /pratiche/{pratica_id}/note` | pratiche |
| `GET /pratiche/{pratica_id}/registro` | pratiche |
| `POST /pratiche/{pratica_id}/restituzione` | pratiche |
| `POST /pratiche/{pratica_id}/stato` | pratiche |
| `GET /pratiche/{pratica_id}/storico` | pratiche |
| `GET /smistamento` | pratiche |
| `GET /fascicoli` | schermate |
| `GET /fascicoli/{codice}/pratiche` | schermate |
| `GET /home` | schermate |
| `GET /temi` | schermate |
| `GET /tipi-collegamento` | schermate |
| `GET /vocabolari` | schermate |
| `GET /salute` | — (database, archivio, coda, motore; vedi Decisioni) |

## Ambiente demo per il frontend

```
export PYTHONPATH=..  ESPOSTI_COOKIE_SECURE=false  ESPOSTI_AMBIENTE=sviluppo
python -m api.demo        # seed + 8 pratiche sintetiche analizzate dal finto motore e assegnate (ripetibile)
uvicorn api.main:app --port 8000
```

`python -m api.esporta_openapi <file>` scrive lo schema da cui il frontend genera i tipi.

## Prove con il finto motore

I pacchetti `documenti` e `motore` sono cartelle sorelle in `backend/`: per
avviare qualcosa fuori da pytest serve `export PYTHONPATH=..` (da `backend/api`).

```
python -m api.prova_motore          # carica documenti sintetici, esegue il worker, stampa i risultati
python -m api.prova_motore esposto_cani.pdf foglio_manoscritto.pdf   # solo alcuni scenari
python -m api.worker --una-volta    # svuota la coda ed esce (senza --una-volta resta in ascolto)
```

`ESPOSTI_MOTORE_URL` vuoto = finto motore nello stesso processo; con un URL
(`http://motore:8080`) il worker parla al servizio HTTP (anche il finto:
`python -m motore.finto`, in ascolto su `MOTORE_FINTO_HOST`:`MOTORE_FINTO_PORTA`, default `0.0.0.0:8080`;
in compose è il servizio `motore-finto`). Il **nome del file** sceglie lo scenario
(elenco in `backend/motore/finto/app.py`): `riscontro`, `manoscritto`/`incerto`,
`errore`/`.pages`, `illeggibile`, `scaduto` (3 tentativi), `instabile` (riesce al
secondo), `occupato` (429 una volta), `invalido` (viola il contratto). L'archivio
locale sta in `ESPOSTI_ARCHIVIO_RADICE` (default `~/.esposti/archivio`, fuori dal repository).
I temporanei del worker stanno in `ESPOSTI_DIR_TEMPORANEA` (creata se manca; ogni lavoro cancella il suo,
all'avvio il worker cancella quelli rimasti da un'interruzione).

## Test

```
scripts/prove.sh backend            # dalla radice: pytest in Docker su PostgreSQL 16 (database esposti_test)
```

I test girano su PostgreSQL vero, con lo schema creato dalle migrazioni.
Con `ESPOSTI_TEST_DATABASE_URL=postgresql+psycopg://…` usano quel database
(in compose: `esposti_test` del servizio `db`); senza, avviano un PostgreSQL temporaneo
con `pgserver`. Ogni test crea dati con nomi unici.

## Decisioni

Decise il 2026-10-21 (le prime tre dal coordinatore, le altre su raccomandazione; motivi in
[docs/diario.md](../../docs/diario.md)).

- **Riassegnazione** ammessa solo in `DA_VALIDARE` (stato invariato, motivo obbligatorio). *Confermata.*
- **Temi proposti dall'IA**: alla validazione quelli che l'operatore non tocca si considerano **accettati**
  (diventano `confermato`, origine `ia`, decisi da chi valida; nel registro `temi.decidi` con `implicito: true`).
  Scartare resta sempre possibile; zero temi confermati è ammesso. Niente più 422 per temi non decisi.
  Fuori dalla validazione (`PUT /temi`) un tema non indicato resta com'è.
- **Valutazione con controllo di versione**: ogni salvataggio incrementa `valutazione.versione`; chi salva
  (PUT `/valutazione` o `/validazione`) rimanda la `versione` letta (`null` se non c'era ancora). Se nel
  frattempo è cambiata: **409** con `detail = {codice: "valutazione_modificata", versione_attuale, messaggio}`
  e nulla cambia; il backoffice mostra un messaggio e ricarica la valutazione aggiornata. Migrazione `0005`.
  Una valutazione ATS già compilata si sostituisce solo con `conferma_sovrascrittura`. I testi liberi
  (`note`, `*_altro`, descrizione attività) non entrano mai nel registro, che conserva prima/dopo.
- **`GET /salute`**: controlla database, archivio (scrittura e cancellazione di un file di prova), coda
  (lavori `in_coda`/`in_corso`) e motore (`GET {MOTORE_URL}/v1/salute`, timeout 2 s, con versione del motore
  e del contratto). **503** solo se database o archivio non funzionano; motore irraggiungibile, non pronto
  (`stato` diverso da `pronto`, es. `non_pronto`) o con contratto di versione principale diversa = `"degradato"`
  con **200** (il lavoro delle persone continua, i
  lavori restano in coda). Nessun URL, percorso o messaggio interno nella risposta.
- Restituzione ammessa da `DA_VALIDARE` e `IN_LAVORAZIONE`: `ufficio_id` torna `NULL`.
- Limite di tentativi di accesso: 5 falliti per nome utente in 15 minuti.
- Un amministratore non può disattivare sé stesso né cambiarsi ruolo.
- Chiuse tutte le analisi la pratica passa da `IN_ANALISI` a `DA_SMISTARE` (anche se il
  motore fallisce): il lavoro umano non si blocca. Si precompilano **solo** `tipo` e, se
  vuoti, protocollo e comune; ufficio, valutazione e temi restano alle persone.
- Errori del motore: ritentabili fino a 3 tentativi; `risultato_non_valido` (fuori
  contratto), `richiesta_non_valida` (422 del motore) e `archivio_non_disponibile` (impronta diversa) non si
  ritentano. Una risposta di stato non `200` con corpo non conforme (500 testuale, 404 di un URL sbagliato) è un
  guasto ritentabile; un corpo conforme vale con qualunque codice (404 del motore riavviato). Si accetta
  qualunque contratto `1.x`.
- Attesa massima di un'analisi: `ESPOSTI_MOTORE_TIMEOUT_SECONDI` = 2100 s, sopra i 1800 s del motore vero.
- Collegamento automatico «stesso protocollo»: serve **numero e anno** (colonna calcolata
  `pratica.chiave_protocollo`, migrazione `0006`): l'anno è quello scritto nel protocollo (`…/AAAA`) o, se
  manca, quello di `data_protocollo`; senza anno nessun collegamento automatico. Vale anche per il conteggio
  delle collegate e per «senza riscontro».
- Il worker vive in `api/worker.py` (ha bisogno del database); il client e il finto sono in `backend/motore`.
- Lettura del testo (`documento.testo`) e del file (`documento.apri`) vanno nel registro.
- Validazione: servono esito e urgenza.
- Attività: solo su pratiche `IN_LAVORAZIONE`; `conclusa`/`annullata` sono definitive.
- «Senza riscontro» (Home) = esposti `IN_LAVORAZIONE` senza una pratica `riscontro_ats` collegata (stesso
  protocollo o collegamento manuale RISCONTRO); il percorso mostra il passo «atteso» anche in `DA_VALIDARE`.
- Collegare richiede di vedere entrambe le pratiche; rimuovere basta vederne una.
- Solo lo smistatore crea pratiche; smistatore e operatore (sulle proprie) aggiungono documenti e rilanciano.
- La demo (`python -m api.demo`) analizza i suoi file sintetici sempre con il finto nello stesso processo,
  anche quando `ESPOSTI_MOTORE_URL` punta al motore vero.
