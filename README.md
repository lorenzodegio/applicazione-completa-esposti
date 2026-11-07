# Gestione esposti — ATS Insubria

Web application interna per la gestione degli esposti: smistamento agli
uffici, validazione e lavorazione da parte degli operatori, fascicoli per
tema, con il supporto di un motore di classificazione esterno (la proposta
dell'IA è solo un suggerimento: decide sempre la persona).

Chi arriva sul progetto parte da [docs/consegna.md](docs/consegna.md).

## Avvio rapido (Docker, da WSL)

```
docker compose up -d --build                         # con il finto motore
MOTORE_URL=http://motore:8080 docker compose up -d   # con il motore vero (rete esposti_interna)
scripts/prove.sh                                     # tutte le prove: backend, frontend, live, end-to-end
docker compose down -v                               # spegne e azzera
```

Backoffice su http://127.0.0.1:5173, API su http://127.0.0.1:8100. Utenti demo, password e dettagli in
[docs/avvio.md](docs/avvio.md); le decisioni prese strada facendo in [docs/diario.md](docs/diario.md).

## Struttura

```
frontend/
  frontoffice/   mockup della parte cittadino (HTML/JS, congelato)
  backoffice/    applicazione operatori (React + Vite + TypeScript)
backend/
  api/           FastAPI + PostgreSQL: pratiche, ruoli, permessi, registro azioni
  motore/        connettore verso il motore (servizio Docker esterno, coda di lavori)
  documenti/     interfaccia unica per l'archivio (cartella locale, poi SharePoint)
e2e/             prove end-to-end nel browser (Playwright) contro lo stack compose
scripts/         prove.sh (tutte le prove in Docker), genera-tipi.sh (OpenAPI → tipi TypeScript)
compose.yml      ambiente completo: db, api, worker, motore-finto, backoffice (+ profilo "prove")
docs/
  avvio.md             come si avvia, si prova, si spegne
  diario.md            decisioni prese strada facendo, con data e motivo
  piano.md             modello dei dati, API, schermate, fasi
  contratto_motore.md  interfaccia applicazione ↔ motore
  consegna.md          per chi arriva sul progetto
  mockups/             schermate di riferimento: Home, Inbox, Fascicolo, Gestione pratiche
  mockup.md            descrizione del primo mockup HTML/JS
  collaudo/            collaudo manuale: checklist, modelli di segnalazione ed esiti, documenti sintetici di prova
```

Il motore di classificazione è un repository separato
(`classificatore-esposti-v2`) e si collega solo tramite il contratto.

## Rami

| Ramo | Uso | Riceve da |
|---|---|---|
| `master` | solo versioni stabili | `dev` |
| `dev` | integrazione | `frontend`, `backend` |
| `frontend`, `backend` | lavoro delle due parti | rami personali |
| `lorenzo`, `khalil` | rami personali | — (si parte dal ramo di area e lì si riporta il lavoro) |

Mai commit diretti su `master`.

## Dati

Solo dati sintetici in sviluppo. Dati, documenti, CSV, file `.env` e uscite
del motore sono esclusi dal repository (vedi `.gitignore`).
