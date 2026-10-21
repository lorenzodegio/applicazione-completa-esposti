# frontend/backoffice

Applicazione degli operatori: **React + Vite + TypeScript**. Parla solo con l'API del backend
(`backend/api`); i permessi li applica il server, qui si decide solo cosa mostrare.

Struttura e testi vengono dai mockup in `docs/mockups/` (colori, Titillium Web, bersagli da 44 px):
sono un riferimento, non codice riusato. Il vecchio mockup HTML di questa cartella
(`dashboard-operatore.html`, `js/`, `styles/`, `assets/`) resta dov'è come riferimento.

## Avvio in sviluppo

```
# 1. backend (da backend/api, vedi il suo README)
export PYTHONPATH=..  ESPOSTI_COOKIE_SECURE=false  ESPOSTI_AMBIENTE=sviluppo
alembic upgrade head
python -m api.demo                 # dati SINTETICI: pratiche già analizzate dal finto motore
uvicorn api.main:app --port 8000

# 2. frontend (da frontend/backoffice)
npm install
npm run dev                        # http://localhost:5173, inoltra /api a http://localhost:8000
```

Accessi demo (password `password-sintetica-1`): `smistatore`, `op.vet`, `op.igp`, `admin`.
Con `VITE_API_URL=http://host:porta npm run dev` il proxy punta altrove. In sviluppo il cookie di
sessione è `Secure` salvo `ESPOSTI_COOKIE_SECURE=false` (Safari non lo accetta su http).

## Schermate

| Rotta | Chi | Cosa |
|---|---|---|
| `/accedi` | tutti | accesso |
| `/` | smistatore, operatore | Home: contatori, ultimi arrivi, fascicoli attivi, disaccordo IA–operatore |
| `/inbox/:id?` | smistatore, operatore | coda + validazione di un esposto alla volta (proposta dell'IA, valutazione precompilata, temi, restituzione) |
| `/pratiche` | smistatore, operatore | Gestione pratiche: ricerca e filtri (nell'URL: `?disaccordo=1`, `?tema=cani`, …) |
| `/pratiche/:id` | smistatore, operatore | scheda: riepilogo, documenti, percorso, collegamenti, azioni, note e registro |
| `/fascicoli/:codice?` | smistatore, operatore | percorso del fascicolo e storico della pratica scelta |
| `/smistamento` | smistatore | assegnazione agli uffici e caricamento di un nuovo esposto |
| `/uffici`, `/utenti` | amministratore | gestione di uffici e utenti (l'amministratore non vede le pratiche) |

## Come è fatto

- `src/api/schema.d.ts` è **generato** dallo schema OpenAPI del backend: se cambia l'API si rigenera e
  `tsc` indica cosa rompe. Per aggiornarlo: `cd backend/api && PYTHONPATH=.. python -m api.esporta_openapi
  ../../frontend/backoffice/openapi.json`, poi `npm run gen:api`.
- `src/api/endpoints.ts`: tutte le chiamate, tipizzate; `client.ts`: `fetch` con gestione errori
  (`ApiError`, un 401 fuori dall'accesso riporta alla pagina di accesso); `errori.ts`: messaggi per l'utente.
- Stato del server con TanStack Query; dopo ogni modifica si invalida la cache (i dati sono piccoli).
- Pagina e filtri nell'URL (si può linkare, funziona il tasto «indietro»).

## Test

```
npm run typecheck && npm test     # veloci: backend simulato (valida i corpi delle richieste, ruoli, accessibilità)
```

I test `src/test/live.test.tsx` renderizzano l'app vera contro un backend vero e si attivano solo con
`LIVE_API_URL` (dopo `python -m api.demo` su un database vuoto):

```
LIVE_API_URL=http://localhost:8000 npm test
```

Modificano i dati demo (validano, assegnano, creano un utente): per rifarli serve un database nuovo.
`axe-core` controlla le regole strutturali di accessibilità; **il contrasto dei colori e l'uso da tastiera
vanno verificati in un browser**.

## Da fare

Importazione ATS (fase 5), ufficio suggerito allo smistamento, esportazioni, accesso Microsoft.
