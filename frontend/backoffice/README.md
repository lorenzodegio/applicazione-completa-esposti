# frontend/backoffice

Applicazione degli operatori: **React + Vite + TypeScript**. Parla solo con l'API del backend
(`backend/api`); i permessi li applica il server, qui si decide solo cosa mostrare.

Struttura e testi vengono dai mockup in `docs/mockups/` (colori, Titillium Web, bersagli da 44 px):
sono un riferimento, non codice riusato. Il vecchio mockup HTML di questa cartella
(`dashboard-operatore.html`, `js/`, `styles/`, `assets/`) resta dov'è come riferimento.

## Avvio in sviluppo

Dalla radice del repository, tutto in Docker (dettagli in [docs/avvio.md](../../docs/avvio.md)):

```
docker compose up -d --build       # http://127.0.0.1:5173 ; il proxy /api va al servizio api
```

`src/` è montata nel container in sola lettura: Vite ricarica al volo. Senza Docker: `npm install`,
`npm run dev` (inoltra `/api` a `http://localhost:8000`, o a `VITE_API_URL`). `VITE_HOST_AMMESSI`
(elenco separato da virgole) aggiunge nomi host accettati da Vite oltre a localhost (in compose:
`backoffice`, per il browser delle prove end-to-end).

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
  `tsc` indica cosa rompe. Per aggiornarlo (in Docker): `scripts/genera-tipi.sh` dalla radice
  (`api.esporta_openapi` → `openapi.json` → `npm run gen:api`).
- La valutazione viaggia con la sua `versione`: a un 409 `valutazione_modificata` Inbox e scheda mostrano
  un messaggio e ricaricano la valutazione salvata da altri (`eConflittoValutazione` in `client.ts`).
- `src/api/endpoints.ts`: tutte le chiamate, tipizzate; `client.ts`: `fetch` con gestione errori
  (`ApiError`, un 401 fuori dall'accesso riporta alla pagina di accesso); `errori.ts`: messaggi per l'utente.
- Stato del server con TanStack Query; dopo ogni modifica si invalida la cache (i dati sono piccoli).
- Pagina e filtri nell'URL (si può linkare, funziona il tasto «indietro»).

## Test

Dalla radice, in Docker:

```
scripts/prove.sh frontend          # npm run typecheck && npm test: backend simulato (corpi delle richieste, ruoli, accessibilità)
scripts/prove.sh live              # src/test/live.test.tsx contro API + worker + finto motore veri, database nuovo
scripts/prove.sh e2e               # Playwright in e2e/: browser vero contro lo stack compose
```

I test `src/test/live.test.tsx` renderizzano l'app vera contro un backend vero e si attivano solo con
`LIVE_API_URL` (dopo `python -m api.demo` su un database vuoto: `scripts/prove.sh live` lo prepara da sé).
Modificano i dati demo (validano, assegnano, creano un utente): per rifarli serve un database nuovo.
`axe-core` controlla le regole strutturali di accessibilità; **il contrasto dei colori e l'uso da tastiera
vanno verificati in un browser**.

## Da fare

Importazione ATS (fase 5), ufficio suggerito allo smistamento, esportazioni, accesso Microsoft.
