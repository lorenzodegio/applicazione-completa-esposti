# CLAUDE.md — Gestione esposti ATS Insubria

Web application interna per la gestione degli esposti. Il motore di
classificazione **non** si sviluppa qui.

## Regole di lavoro (vincolanti)

- **Mai commit diretti su `master`.** Dichiara sempre su quale ramo stai lavorando.
- **Nessun commit senza OK esplicito**: mostra prima l'elenco di ciò che entra.
- **Nessun push**: lo fa l'utente, oppure lo chiede esplicitamente.
- **Solo dati sintetici** in sviluppo. Nessun dato reale in chat, log, test o repository.
- `frontend/frontoffice/` (parte cittadino del mockup): **non toccarla e non ragionarci.**
- Il motore vero sta in `/home/lorenzo/classificatore-esposti-v2`, fuori dal
  repository: **non copiarlo, non leggerne i dati, non montarne le cartelle di lavoro.**
- Git si usa dall'interno di WSL (`wsl git ...`), non dal git di Windows sul percorso UNC.

## Flusso dei rami

```
lorenzo / khalil ─► frontend ─┐
                  ─► backend ──┴─► dev ─► master
```

- `master`: solo versioni stabili; riceve solo da `dev`.
- `dev`: integrazione; riceve da `frontend` e `backend`.
- `frontend`, `backend`: lavoro delle due parti.
- `lorenzo`, `khalil`: rami personali; si parte dal ramo di area su cui si
  lavora e lì si riporta il lavoro.

## Struttura

- `frontend/frontoffice/` — mockup cittadino (congelato).
- `frontend/backoffice/` — applicazione operatori: **React + Vite + TypeScript**,
  riusando lo stile del mockup (il mockup operatore resta come riferimento).
- `backend/api/` — **FastAPI + PostgreSQL**.
- `backend/motore/` — solo il **connettore** verso il motore: servizio Docker
  separato, chiamato tramite **coda di lavori, uno alla volta**. All'inizio un
  finto motore con la stessa forma di dati.
- `backend/documenti/` — **interfaccia unica** di lettura/scrittura documenti;
  implementazione su cartella locale, poi SharePoint (struttura da definire).
- `docs/` — piano e documentazione.

## Ruoli e permessi

- **smistatore**: vede tutte le pratiche in arrivo, le assegna a un ufficio, può riassegnare.
- **operatore**: appartiene a un ufficio e vede **solo** le pratiche smistate al suo ufficio.
- **amministratore**: gestisce uffici e utenti.
- I permessi si applicano **nel server**, mai solo nel browser, e vanno **coperti da test**.
- Accesso: utenti locali con ruolo per ora, predisposto per l'accesso Microsoft di ATS.

## La pratica

Ogni pratica mostra:
- documenti;
- testo estratto;
- scheda precompilata;
- proposta dell'IA con il motivo (**è un suggerimento: decide sempre la persona**);
- avviso di lettura incerta;
- storico di assegnazioni e stati;
- note interne;
- collegamenti con altre pratiche: automatici per stesso protocollo, più quelli
  aggiunti a mano, ciascuno con il suo tipo.

**Ogni azione finisce in un registro: chi, cosa, quando.**
