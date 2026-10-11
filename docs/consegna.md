# Consegna — per chi arriva sul progetto

Benvenuto Khalil. Questo documento ti dà quello che serve per partire oggi.
Il resto è in [piano.md](piano.md) (cosa costruiamo) e
[contratto_motore.md](contratto_motore.md) (il tuo punto di partenza).

---

## 1. Il progetto in breve

Web application **interna** di ATS Insubria per gestire gli **esposti**
(segnalazioni dei cittadini, inoltri di altri enti, riscontri di ATS).

Il percorso di un esposto:

1. arriva (oggi: caricamento a mano o importazione da una cartella);
2. il **motore di classificazione** lo legge e propone scheda, esito,
   urgenza, azione e tema;
3. lo **smistatore** lo assegna a un ufficio;
4. l'**operatore** dell'ufficio lo valida nella Inbox (la proposta dell'IA
   è accanto al modulo precompilato: **decide sempre la persona**), poi lo
   lavora fino al riscontro.

Le pratiche si raccolgono per tema nei **fascicoli** (Cani, Gatti e colonie
feline, Animali da reddito, Avvelenamenti…). Ogni pratica mostra il suo
percorso: esposto, inoltro, proposta, smistamento, validazione, azioni,
riscontro.

Ruoli: **smistatore** (vede tutto, assegna), **operatore** (vede solo il suo
ufficio), **amministratore** (solo uffici e utenti, non vede le pratiche).

---

## 2. I due repository

| | Questo repository | Il motore |
|---|---|---|
| Nome | `applicazione-completa-esposti` | `classificatore-esposti-v2` |
| Dove | GitHub `lorenzodegio/applicazione-completa-esposti` | sulla macchina ATS, in `/home/lorenzo/classificatore-esposti-v2` |
| Contenuto | backoffice, API, connettore verso il motore, archivio documenti | la classificazione vera (lettura, OCR, scheda, proposta) |
| Gira come | servizi Docker `api`, `worker`, `db`, `backoffice` | **servizio Docker separato** |

I due repository restano **separati**. Comunicano solo via HTTP secondo il
[contratto del motore](contratto_motore.md):

- in questo repository **non si copia** codice del motore, **non si leggono**
  i suoi dati e **non si montano** le sue cartelle di lavoro;
- il motore non legge il nostro database né il nostro archivio: riceve un
  documento alla volta e restituisce un risultato.

---

## 3. Il tuo compito: collegare i due

Far parlare applicazione e motore **tramite il contratto**. In pratica:

1. **Contratto eseguibile** — in `backend/motore/contratto/`: uno schema
   JSON del risultato e degli errori, più gli esempi sintetici del contratto
   come file di prova. È la base dei test di entrambe le parti.
2. **Finto motore** — in `backend/motore/finto/`: un piccolo servizio che
   implementa le quattro chiamate del contratto con risposte sintetiche e
   deterministiche. Deve coprire: lettura pulita, lettura incerta, riscontro,
   errore, motore occupato (`429`). Il resto dell'applicazione lo usa
   finché non c'è il motore vero.
3. **Connettore** — in `backend/motore/`: l'interfaccia `ClientMotore` con
   `MotoreFinto`/`MotoreHttp`, e il **worker** che prende **un lavoro alla
   volta** dalla coda, scarica il documento in una cartella temporanea,
   verifica l'impronta, lo invia, salva il risultato e **cancella sempre** il
   temporaneo. Tempo massimo, tre tentativi, poi pratica in `DA_SMISTARE` con
   avviso.
4. **Lato motore** — nel repository del motore (con le sue regole), esporre
   le chiamate del contratto come servizio Docker. Questo lavoro **non**
   entra qui.
5. **Test di contratto** — la stessa suite gira contro il finto (sempre, anche
   in CI) e contro il motore vero sulla macchina ATS, **solo con documenti
   sintetici**.

Il contratto l'abbiamo scritto noi senza guardare il motore: se il motore
oggi produce qualcosa di diverso, è normale. Le differenze si risolvono
**adattando il motore o modificando il contratto**, non aggirandolo nel
connettore. Ogni modifica al contratto passa da `backend` con revisione, e
aggiorna `versione_contratto`.

**Puoi partire subito**: il connettore non dipende dal server di base (fase 1),
che procede in parallelo. Il punto d'incontro con il server è la tabella
`lavoro_motore` e i campi di `risultato_motore`
([piano](piano.md#34-motore)): se ti serve cambiarli, si concorda prima.

---

## 4. Cosa c'è in ogni cartella

```
CLAUDE.md                 regole di lavoro (le legge anche Claude Code)
README.md                 struttura e rami, in breve
docs/
  piano.md                modello dei dati, API, schermate, fasi
  contratto_motore.md     interfaccia applicazione ↔ motore
  consegna.md             questo documento
  mockups/                le 4 schermate di riferimento (Home, Inbox, Fascicolo, Gestione pratiche)
  mockup.md               descrizione del primo mockup HTML/JS
frontend/
  frontoffice/            mockup della parte cittadino — congelato, non si tocca
  backoffice/             mockup della parte operatore — solo riferimento; qui nascerà l'app React
backend/
  api/                    FastAPI + PostgreSQL (ancora vuoto)
  motore/                 connettore verso il motore ← il tuo lavoro
  documenti/              interfaccia unica per l'archivio (cartella locale, poi SharePoint)
```

I mockup in `docs/mockups/` sono esportati da un editor di design: per
vederli servi **la cartella `docs/mockups/`** (`cd docs/mockups && python3 -m
http.server`) e apri `home/Main.dc.html`; il menu porta alle altre
schermate. Sono un riferimento per struttura, testi, colori e carattere
(Titillium Web), **non codice da riusare**.

Oggi nel repository **non c'è ancora codice applicativo**: solo struttura,
documentazione e mockup.

---

## 5. Rami e regole

```
khalil / lorenzo ─► frontend ─┐
                 ─► backend ──┴─► dev ─► master
```

- `master`: solo versioni stabili, riceve solo da `dev`. **Mai commit diretti.**
- `dev`: integrazione, riceve da `frontend` e `backend`.
- `frontend`, `backend`: le due parti.
- `khalil`, `lorenzo`: rami personali. Si parte dal ramo di area su cui si
  lavora e lì si riporta il lavoro. Per te: `khalil` riallineato a `backend`,
  poi merge in `backend`.

Oggi tutti i rami di lavoro sono allineati a `dev`; `master` è al primo commit.

Regole che valgono sempre:

- **Solo dati sintetici.** Nessun dato reale (documenti, nomi, recapiti,
  protocolli veri, il CSV delle valutazioni ATS) in repository, chat, log,
  test o issue. Esiste un CSV reale di valutazioni ATS: **non si apre** in
  sviluppo; l'importazione si prova su un CSV sintetico con le stesse colonne.
- **Permessi nel server**, mai solo nel browser, sempre con test.
- **La proposta dell'IA è un suggerimento**: niente automatismi che
  assegnino, validino o chiudano al posto di una persona.
- **Registro di tutto**: ogni azione scrive chi, cosa, quando.
- **I documenti stanno in archivio** (SharePoint); sulla macchina solo il
  tempo dell'elaborazione, poi si cancellano.
- `.env`, dati, documenti e uscite del motore sono esclusi da `.gitignore`:
  non forzarli.
- Su Windows con WSL usa **git dentro WSL**, non il git di Windows sul
  percorso `\\wsl.localhost\…`.

---

## 6. Cosa è deciso e cosa è aperto

**Deciso**
- Architettura: React + Vite + TypeScript; FastAPI + PostgreSQL; motore come
  servizio Docker separato con coda di lavori, uno alla volta; archivio
  dietro interfaccia unica.
- Ruoli e visibilità (piano, sezione 6); collegamenti verso altri uffici
  visibili solo come numero, ufficio, stato.
- Contratto del motore 1.1, con risultato **per documento**.
- Elenchi del modulo ATS (ambito, problematica, elementi, esito, urgenza,
  azione) e tipi di documento, compresa la **lettera avvocato**. Per
  l'ambito ci sono due elenchi: quello attuale, che il motore deve produrre,
  e quello storico usato nelle valutazioni già compilate, con la
  corrispondenza dal vecchio al nuovo (contratto, sezione 4.1).
- Valutazione dell'operatore distinta dalla proposta dell'IA; importazione
  delle valutazioni ATS per nome file e poi per protocollo, solo conteggi,
  mai sovrascrivere.
- SharePoint archivio di riferimento; testo estratto accanto al documento;
  migrazione con verifica delle impronte.
- Menu: Home, Inbox, Fascicoli, Gestione pratiche (+ Smistamento).

**Aperto** (dettaglio nel [piano](piano.md#11-questioni-aperte))
- Formato tecnico del CSV ATS (separatore, codifica, date).
- **Come riusare la scomposizione delle celle a scelta multipla** già
  presente nel motore (`cerchio1/voci.py`): l'importazione delle valutazioni
  ATS deve usare quella logica, ma senza copiarla qui. La strada preferita è
  pubblicarla dal motore come piccolo pacchetto versionato; in alternativa,
  una chiamata del motore ([piano, 5.3](piano.md#53-valutazioni-già-fatte-da-ats)).
  Tocca a te proporre come.
- Regola di raggruppamento dei file nell'importazione da cartella.
- Struttura di SharePoint.
- Ricerca nel testo estratto.
- Per te in particolare: **quanto il motore attuale è lontano dal contratto**.
  Annota le differenze e proponi come chiuderle.

---

## 7. Da dove partire

1. Clona il repository e passa al tuo ramo: `git switch khalil`.
2. Leggi [CLAUDE.md](../CLAUDE.md), poi [contratto_motore.md](contratto_motore.md),
   poi le sezioni 3.4, 4 e 9 del [piano](piano.md).
3. Apri il mockup Inbox per vedere come vengono mostrati proposta, motivo,
   frase e avviso di lettura incerta: è il prodotto finale del tuo lavoro.
4. Scrivi schema e file di prova del contratto, poi il finto motore.
5. Confronta il contratto con quello che il motore produce oggi e annota le
   differenze.
6. Porta il lavoro su `backend` (merge da `khalil`), poi in `dev` quando i
   test sono verdi.

Per dubbi su decisioni di prodotto: Lorenzo. Per il contratto: proponi la
modifica nel documento, su `backend`, prima di scrivere il codice.
