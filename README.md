# Gestione esposti — ATS Insubria

Web application interna per la gestione degli esposti: smistamento agli
uffici, lavorazione da parte degli operatori, supporto di un motore di
classificazione esterno (la proposta dell'IA è solo un suggerimento).

## Struttura

```
frontend/
  frontoffice/   mockup della parte cittadino (HTML/JS, solo riferimento, congelato)
  backoffice/    applicazione operatori (React + Vite + TypeScript) — oggi: mockup di riferimento
backend/
  api/           FastAPI + PostgreSQL: pratiche, ruoli, permessi, registro azioni
  motore/        connettore verso il motore di classificazione (servizio Docker esterno, coda di lavori)
  documenti/     interfaccia unica per i documenti (cartella locale, poi SharePoint)
docs/            piano e documentazione
```

## Rami

| Ramo | Uso | Riceve da |
|---|---|---|
| `master` | solo versioni stabili | `dev` |
| `dev` | integrazione | `frontend`, `backend` |
| `frontend`, `backend` | lavoro delle due parti | rami personali |
| `lorenzo`, `khalil` | rami personali | — (si parte dal ramo di area e lì si riporta il lavoro) |

Mai commit diretti su `master`.

## Dati

Solo dati sintetici in sviluppo. Dati, documenti, file `.env` e uscite del
motore sono esclusi dal repository (vedi `.gitignore`).
