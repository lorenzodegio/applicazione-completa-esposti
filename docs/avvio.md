# Avvio e prove

Tutto gira in **Docker**, dall'interno di WSL (`cd ~/applicazione-completa-esposti`). Niente venv,
niente `pip`/`npm` sull'host. Solo dati **sintetici**.

Il modo raccomandato è il `compose.yml` nella radice. I `.bat` di `runningScripts/` restano per chi
lavora senza Docker, ma non sono più la strada principale.

## Una volta sola

La rete dove si aggancia il motore vero è condivisa fra i due repository ed è **interna** (senza internet).
Se non c'è ancora:

```
docker network create --internal esposti_interna
```

## Avvio con il finto motore

```
docker compose up -d --build
```

| Servizio | Cosa fa | Dove |
|---|---|---|
| `db` | PostgreSQL 16 (volume `pgdata`) | solo in rete Docker |
| `api` | migrazioni + demo sintetica all'avvio, poi FastAPI | http://127.0.0.1:8100/api/v1 (documentazione su `/docs`) |
| `worker` | coda dei lavori, un documento alla volta | reti `default` ed `esposti_interna` |
| `motore-finto` | finto motore, contratto 1.1, porta 8080 | `http://motore-finto:8080` (solo in rete Docker) |
| `backoffice` | Vite, inoltra `/api` all'API | http://127.0.0.1:5173 |

La porta 8000 dell'host è occupata da un servizio di Windows: per questo l'API è pubblicata su **8100**.
L'archivio dei documenti sta nel volume `archivio` (mai nel repository).

Dopo una modifica al backend: `docker compose up -d --build`. I sorgenti del backoffice (`src/`) sono
montati in sola lettura: Vite ricarica al volo; dopo un cambio di dipendenze serve `--build`.

Stato: `curl -s http://127.0.0.1:8100/api/v1/salute` (database, archivio, coda, motore con versioni;
`503` solo se database o archivio non funzionano, motore assente = `"degradato"` con `200`).

## Avvio con il motore vero

Il motore vero (repository `classificatore-esposti-v2`) è un servizio `motore`, porta 8080, agganciato
alla rete `esposti_interna`. Si avvia dal suo repository; qui basta indicare l'URL:

```
MOTORE_URL=http://motore:8080 docker compose up -d
```

`MOTORE_URL` diventa `ESPOSTI_MOTORE_URL` di `api` (per `/salute`) e `worker`. Senza la variabile si usa
`http://motore-finto:8080`. Lo stack parte anche se il motore vero non c'è: i lavori restano in coda e
`/salute` dice `"motore": {"stato": "irraggiungibile"}`. Per tornare al finto: `docker compose up -d`.

La demo dell'avvio (`python -m api.demo`) usa **sempre** il finto nello stesso processo: i suoi file sono
sintetici, fatti per gli scenari del finto. Al motore vero arrivano solo i documenti caricati dal backoffice.

## Utenti demo

Password di tutti: `password-sintetica-1` (solo sviluppo).

| Utente | Ruolo |
|---|---|
| `smistatore` | smistatore (vede tutto, assegna, carica nuovi esposti) |
| `op.vet` | operatore di Medicina Veterinaria |
| `op.igp` | operatore di Igiene pubblica |
| `admin` | amministratore (uffici e utenti, non vede le pratiche) |

La demo crea 8 pratiche sintetiche analizzate dal finto e ne assegna alcune agli uffici. È ripetibile:
se c'è già, non rifà nulla.

## Prove

Ogni suite gira in un **progetto compose separato** (`esposti-prove-<suite>`), con database su tmpfs,
archivio nuovo, nessuna porta sull'host e sempre il finto motore; alla fine si cancella tutto. Si possono
lanciare anche con lo stack di sviluppo acceso.

```
scripts/prove.sh                 # tutte, nell'ordine qui sotto
scripts/prove.sh backend         # pytest su PostgreSQL (database esposti_test)
scripts/prove.sh frontend        # tsc (typecheck) + vitest unit (backend simulato)
scripts/prove.sh live            # vitest: l'app vera contro API + worker + finto via HTTP, dati demo
scripts/prove.sh e2e             # Playwright (Chromium vero) contro lo stack completo
```

L'end-to-end (`e2e/`, immagine `mcr.microsoft.com/playwright:v1.63.0-noble`, `@playwright/test` 1.63.0)
carica dal backoffice un documento per ciascuno dei 9 scenari del finto (lettura pulita, riscontro,
manoscritto/incerto, formato non supportato, illeggibile, tempo scaduto, instabile, occupato, fuori
contratto), aspetta che il worker svuoti la coda, controlla nel backoffice testo, scheda, proposta,
avvisi ed errori, poi smistamento, validazione nella Inbox (temi accettati), percorso a pallini e
conflitto di versione fra due persone sulla stessa valutazione.

## Rigenerare schema OpenAPI e tipi del frontend

Dopo una modifica all'API:

```
scripts/genera-tipi.sh           # backend/api → frontend/backoffice/openapi.json → src/api/schema.d.ts
```

## Spegnere e azzerare

```
docker compose down              # spegne, i dati restano
docker compose down -v           # spegne e cancella database e archivio (al prossimo avvio: demo nuova)
```

Se una prova si interrompe a metà: `docker compose -p esposti-prove-e2e down -v` (o `-backend`,
`-frontend`, `-live`), anche se `scripts/prove.sh` lo fa da solo alla successiva esecuzione.
