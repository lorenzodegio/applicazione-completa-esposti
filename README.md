# Gestione esposti — ATS Insubria

Web application interna per la gestione degli esposti: smistamento agli
uffici, validazione e lavorazione da parte degli operatori, fascicoli per
tema, con il supporto di un motore di classificazione esterno (la proposta
dell'IA è solo un suggerimento: decide sempre la persona).

Chi arriva sul progetto parte da [docs/consegna.md](docs/consegna.md).

## Struttura

```
frontend/
  frontoffice/   mockup della parte cittadino (HTML/JS, congelato)
  backoffice/    applicazione operatori (React + Vite + TypeScript) — oggi: mockup di riferimento
backend/
  api/           FastAPI + PostgreSQL: pratiche, ruoli, permessi, registro azioni
  motore/        connettore verso il motore (servizio Docker esterno, coda di lavori)
  documenti/     interfaccia unica per l'archivio (cartella locale, poi SharePoint)
docs/
  piano.md             modello dei dati, API, schermate, fasi
  contratto_motore.md  interfaccia applicazione ↔ motore
  consegna.md          per chi arriva sul progetto
  mockups/             schermate di riferimento: Home, Inbox, Fascicolo, Gestione pratiche
  mockup.md            descrizione del primo mockup HTML/JS
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
