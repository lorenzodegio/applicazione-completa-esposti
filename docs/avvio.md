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
| `motore-finto` | finto motore, contratto 1.2, porta 8080 | `http://motore-finto:8080` (solo in rete Docker) |
| `backoffice` | Vite, inoltra `/api` all'API | http://127.0.0.1:5173 |

La porta 8000 dell'host è occupata da un servizio di Windows: per questo l'API è pubblicata su **8100**.
L'archivio dei documenti sta nel volume `archivio` (mai nel repository).

Dopo una modifica al backend: `docker compose up -d --build`. I sorgenti del backoffice (`src/`) sono
montati in sola lettura: Vite ricarica al volo; dopo un cambio di dipendenze serve `--build`.

Stato: `curl -s http://127.0.0.1:8100/api/v1/salute` (database, archivio, coda, motore con versioni;
`503` solo se database o archivio non funzionano; motore assente, non pronto o con contratto di altra versione
principale = `"degradato"` con `200`).

## Avvio con il motore vero

Il motore vero (repository `classificatore-esposti-v2`) è un servizio `motore`, porta 8080, agganciato
alla rete `esposti_interna`. Si avvia dal suo repository; qui basta indicare l'URL:

```
MOTORE_URL=http://motore:8080 docker compose up -d
```

`MOTORE_URL` diventa `ESPOSTI_MOTORE_URL` di `api` (per `/salute`) e `worker`.
L'applicazione aspetta ogni analisi fino a `ESPOSTI_MOTORE_TIMEOUT_SECONDI` (default **2100 s**), più del
tempo massimo del motore vero (`tempo_max_s = 1800`, circa 45 s per pagina trascritta): così è il motore a
dichiarare `tempo_scaduto`, non l'applicazione. I temporanei del worker stanno su tmpfs (`/tmp/esposti-lavoro`). Senza la variabile si usa
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

### Prova di aggancio con il motore vero

Usa la GPU (tramite il motore), dura alcuni minuti e **non** fa parte di `scripts/prove.sh`. Solo
documenti sintetici: quelli del motore (`classificatore-esposti-v2/tests/dati_sintetici`), montati in sola
lettura nel solo container della prova (`MOTORE_DATI_SINTETICI` per un altro percorso).

```
# 1. nel repository del motore (avvia anche Ollama; servizio "motore" sulla rete esposti_interna)
cd ~/classificatore-esposti-v2 && docker compose up -d motore
# 2. da qui: progetto separato e pulito (esposti-aggancio), worker e api verso http://motore:8080
scripts/prova-motore-vero.sh
```

Cosa fa (`e2e/motore-vero/aggancio.spec.ts`, `compose.motore-vero.yml`):
1. `/salute`: il motore vero risponde, è pronto, contratto `1.x`;
2. lo smistatore carica dal backoffice 6 documenti sintetici: PDF digitale, Word, email inoltrata
   scansionata, tre fogli scritti a mano;
3. il worker li manda al motore uno alla volta; la prova aspetta ogni risultato e stampa il tempo di
   analisi per documento;
4. per ogni documento: lettura incerta sui fogli a mano e non sulle stampe, scheda con frase e pagina
   per ogni voce, proposta con motivo e domanda decisiva, temi del vocabolario con frase, testo letto per
   pagina (dall'archivio);
5. smistamento a Medicina Veterinaria e Inbox dell'operatore: ogni documento c'è, con proposta, valutazione
   precompilata (esito e urgenza della proposta), temi proposti e avviso di lettura incerta.

Prima esecuzione (2026-10-21, 12/12 superati, modelli già caricati): digitale 22 s, Word 18 s, scansione di
2 pagine 72 s, fogli a mano 40–46 s; circa 4 minuti in tutto.

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
