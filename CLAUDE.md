# CLAUDE.md — Gestione esposti ATS Insubria

Web application interna per la gestione degli esposti. Il motore di
classificazione **non** si sviluppa qui: si collega tramite
[docs/contratto_motore.md](docs/contratto_motore.md).

Documenti da conoscere: [docs/piano.md](docs/piano.md) (modello dei dati,
API, schermate, fasi), [docs/consegna.md](docs/consegna.md) (per chi arriva).

## Regole di lavoro (vincolanti)

- **Mai commit diretti su `master`.** Dichiara sempre su quale ramo stai lavorando.
- **Nessun commit senza OK esplicito**: mostra prima l'elenco di ciò che entra.
- **Nessun push** se non richiesto esplicitamente.
- **Solo dati sintetici** in sviluppo. Nessun dato reale in chat, log, test o repository.
- **Il CSV reale delle valutazioni ATS non si apre mai** (né per leggerlo né
  per "dare un'occhiata"). Si lavora su un CSV sintetico con le stesse colonne;
  sui dati reali l'importazione produce **solo conteggi**.
- `frontend/frontoffice/` (parte cittadino del mockup): **non toccarla e non ragionarci.**
- Il motore vero sta in `/home/lorenzo/classificatore-esposti-v2`, fuori dal
  repository: **non copiarlo, non leggerne i dati, non montarne le cartelle di lavoro.**
  Il contatto è solo il contratto HTTP.
- `docs/mockups/` sono file di un editor di design: riferimento per struttura,
  testi, colori e carattere (Titillium Web), **non codice da riusare**.
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
  stile dai mockup in `docs/mockups/` (il mockup HTML resta come riferimento).
- `backend/api/` — **FastAPI + PostgreSQL**.
- `backend/motore/` — solo il **connettore** verso il motore: servizio Docker
  separato, **coda di lavori, un documento alla volta**; finto motore con la
  stessa forma di dati per sviluppo e test.
- `backend/documenti/` — **interfaccia unica** per l'archivio: cartella locale
  ora, **SharePoint come archivio di riferimento** poi.
- `docs/` — piano, contratto, consegna, mockup.

## Ruoli e permessi

- **smistatore**: vede tutte le pratiche, le assegna a un ufficio, può riassegnare.
- **operatore**: appartiene a un ufficio e vede **solo** le pratiche smistate al
  suo ufficio. Delle pratiche collegate di altri uffici vede solo numero,
  ufficio e stato.
- **amministratore**: gestisce uffici e utenti; **non vede le pratiche**.
- I permessi si applicano **nel server**, mai solo nel browser, e vanno **coperti da test**.
- Accesso: utenti locali con ruolo per ora, predisposto per l'accesso Microsoft di ATS.

## La pratica

- Documenti (in archivio, con identificativo SharePoint e impronta) e testo
  estratto per pagina (accanto al documento in archivio, non nel database).
- Scheda precompilata con la frase che giustifica ogni voce.
- **Proposta dell'IA** con motivo e domanda decisiva: **è un suggerimento,
  decide sempre la persona**.
- **Valutazione dell'operatore**, distinta dalla proposta, con origine
  (applicazione o importazione ATS), autore e data.
- Avviso di lettura incerta.
- Uno o più **temi** (proposti dall'IA, confermati dall'operatore) → **fascicoli**.
- **Percorso**: esposto, inoltro, proposta, smistamento, validazione, azioni,
  riscontro (anche "atteso").
- Storico di assegnazioni e stati, note interne, collegamenti (automatici per
  stesso protocollo + manuali con tipo).

**Ogni azione finisce in un registro: chi, cosa, quando.**

## Archivio

SharePoint è l'archivio di riferimento; la macchina **elabora soltanto**:
scarico temporaneo, elaborazione, salvataggio, cancellazione. Nel database:
scheda, proposta, valutazione, stati. Le migrazioni di archivio verificano le
impronte prima di ogni cancellazione.

## Backoffice

Menu: Home (cruscotto), Inbox (validazione di un esposto alla volta),
Fascicoli, Gestione pratiche; lo smistatore ha in più Smistamento.
