# Collaudo manuale — checklist

Per chi prova l'applicazione nel browser, passo per passo, **senza leggere il codice**.
Collaudano **Khalil** e **Syed**. Se è la prima volta che vedi il progetto, leggi tutta la parte 1 prima di
cominciare: basta questa pagina.

- [1. Prima di cominciare](#1-prima-di-cominciare)
- [2. Preparare l'ambiente](#2-preparare-lambiente)
- [3. Utenti di prova](#3-utenti-di-prova)
- [4. Documenti di prova](#4-documenti-di-prova)
- [5. Come registrare gli esiti e segnalare un problema](#5-come-registrare-gli-esiti-e-segnalare-un-problema)
- [6. Chi fa cosa](#6-chi-fa-cosa)
- [7. Le prove](#7-le-prove)

---

## 1. Prima di cominciare

### Cos'è l'applicazione, in breve
Gestione degli **esposti** (segnalazioni) per ATS Insubria. Un esposto arriva come documento (PDF, Word,
RTF), diventa una **pratica** e un **motore** lo legge e propone una valutazione. Poi:

1. lo **smistatore** carica i documenti e assegna ogni pratica a un **ufficio**;
2. l'**operatore** dell'ufficio la trova nella sua **Inbox**, vede la **proposta dell'IA** accanto al modulo
   già compilato, corregge e **conferma** (la proposta è solo un suggerimento: decide sempre la persona);
3. la pratica va avanti con le **azioni** dell'ufficio fino al **riscontro** e alla chiusura;
4. le pratiche si raggruppano per **tema** (Cani, Gatti e colonie feline, Animali da reddito,
   Avvelenamenti) nei **fascicoli**;
5. ogni azione finisce nel **registro**: chi, cosa, quando.

Due motori:
- **finto motore**: risponde subito con risultati di esempio; il **nome del file** decide cosa succede
  (vedi sezione 4). Serve per provare tutti i casi in pochi secondi.
- **motore vero**: legge davvero il documento (anche scritto a mano) con l'IA in locale; ci mette da
  20 secondi a qualche minuto per documento. Gira **solo sulla workstation ATS** (scheda grafica).

### Regole per i tester (valgono sempre)
- **Solo dati sintetici.** Mai documenti reali, **nemmeno sulla workstation ATS**: usa soltanto i file
  della sezione 4. Se per errore carichi un documento reale, fermati, avvisa Lorenzo e azzera l'ambiente
  (sezione 2.4).
- **Una segnalazione per problema**, come issue su GitHub con il modello «Problema di collaudo»: codice
  della prova, passi, atteso, ottenuto. **Screenshot solo di dati sintetici** (controlla che nella schermata
  non ci sia altro: posta, altre finestre, nomi di file personali).
- Non correggere il codice durante il collaudo: si segnala e basta.
- **Khalil e Syed non usano lo stesso ambiente nello stesso momento**: lo svuotamento e le prove di uno
  cambiano i dati dell'altro. Le prove col finto motore si possono fare ognuno sul proprio PC con Docker;
  quelle col **motore vero** solo sulla workstation ATS, **una persona alla volta** (la scheda grafica è una).
- Alla fine ognuno compila il riepilogo in `docs/collaudo/esiti-<nome>.md` (sezione 5).

### Termini che trovi nelle prove
| Termine | Significato |
|---|---|
| Pratica | Un esposto nell'applicazione, con i suoi documenti; ha un numero `ESP-AAAA-NNNNNN` |
| Stato | *In analisi* → *Da smistare* → *Da validare* → *In lavorazione* → *Chiusa* |
| Smistamento | Pagina dello smistatore: carica documenti e assegna le pratiche agli uffici |
| Inbox | Pagina dell'operatore: valuta un esposto alla volta |
| Proposta dell'IA | Ciò che il motore suggerisce (esito, urgenza, azione, motivo); non è mai una decisione |
| Valutazione | Ciò che decide l'operatore (parte dalla proposta) |
| Lettura incerta | Il motore non è sicuro di aver letto bene (es. scrittura a mano): va controllato l'originale |
| Fascicolo | Tutte le pratiche di un tema, in ordine di tempo |
| Percorso | La storia della pratica a pallini: esposto, inoltro, proposta, smistamento, validazione, azioni, riscontro |

---

## 2. Preparare l'ambiente

Tutto si fa **dall'interno di WSL** (finestra «Ubuntu» o terminale di VS Code collegato a WSL), nella
cartella del repository. I comandi completi e le spiegazioni sono in [docs/avvio.md](../avvio.md).

### 2.1 Una volta sola
```
cd ~/applicazione-completa-esposti
git switch dev && git pull                       # versione da collaudare
docker network create --internal esposti_interna # se dice "already exists" va bene
```

### 2.2 Avvio con il finto motore e i dati di prova (DEMO=1)
```
cd ~/applicazione-completa-esposti
DEMO=1 docker compose up -d --build
```
Aspetta 1–2 minuti, poi controlla:
- apri **http://127.0.0.1:8100/api/v1/salute** → deve comparire `"stato":"ok"` e, nel motore,
  `"versione_motore":"finto-1.0.0"`;
- apri **http://127.0.0.1:5173** → pagina «Accedi al backoffice».

`DEMO=1` crea all'avvio due uffici (Medicina Veterinaria, Igiene pubblica), quattro utenti e una ventina di
pratiche sintetiche in stati diversi (titoli che finiscono con `_demo` e alcune senza proposta dell'IA).

### 2.3 Avvio con il motore vero (solo workstation ATS, una persona alla volta)
```
cd ~/classificatore-esposti-v2 && docker compose up -d motore     # avvia anche l'IA locale (Ollama)
cd ~/applicazione-completa-esposti && MOTORE_URL=http://motore:8080 DEMO=1 docker compose up -d
```
Controlla **http://127.0.0.1:8100/api/v1/salute**: motore `"stato":"ok"`, `"versione_motore":"2.2.0"`,
`"versione_contratto":"1.2"`. Il primo documento dopo l'avvio impiega circa un minuto in più (carica i modelli).

Per tornare al finto motore: `cd ~/applicazione-completa-esposti && DEMO=1 docker compose up -d`.

### 2.4 Ripartire puliti
Consigliato all'inizio di ogni sessione e prima delle aree che contano le pratiche (Home, Gestione pratiche).

**Azzeramento completo** (cancella tutto e ricrea i dati di prova):
```
docker compose down -v
DEMO=1 docker compose up -d --build        # aggiungi MOTORE_URL=http://motore:8080 per il motore vero
```

**Solo pratiche, documenti e registro** (restano uffici e utenti, anche quelli creati durante il collaudo):
```
docker compose stop worker
docker compose exec api python -m api.azzera --conferma
docker compose restart api                  # con DEMO=1 ricrea le pratiche di prova
docker compose start worker
```

### 2.5 Browser
Chrome o Edge aggiornati. Per le prove con **due persone insieme** usa due browser diversi (Edge e Chrome)
oppure una finestra normale e una **InPrivate/Incognito**: nello stesso browser i due accessi si
sovrascrivono.

La pagina tecnica delle API è **http://127.0.0.1:8100/docs**. Attenzione: chi accede da `/docs` cambia
l'utente anche nel backoffice dello stesso browser. Per le prove da `/docs` usa **sempre una finestra
InPrivate/Incognito separata**.

**Come accedere da `/docs`**: apri `POST /api/v1/auth/login` → *Try it out* → nel corpo scrivi
`{"username": "op.igp", "password": "password-sintetica-1"}` → *Execute*: risposta `200`. Da quel momento
le chiamate da `/docs` sono fatte con quell'utente. Per gli identificativi da usare nelle prove:
l'**id di una pratica** è l'ultima parte dell'indirizzo della sua pagina (`/pratiche/<id>`); l'**id di un
documento** è nel link «Apri» della scheda *Documenti* (tasto destro → copia indirizzo: `/documenti/<id>/contenuto`).

---

## 3. Utenti di prova

Indirizzo: **http://127.0.0.1:5173**. Password di tutti: **`password-sintetica-1`** (solo per questo ambiente).

| Utente | Ruolo | Ufficio | Menu che deve vedere |
|---|---|---|---|
| `smistatore` | smistatore | — | Home, Inbox, Fascicoli, Gestione pratiche, **Smistamento** |
| `op.vet` | operatore | Medicina Veterinaria | Home, Inbox, Fascicoli, Gestione pratiche |
| `op.igp` | operatore | Igiene pubblica | Home, Inbox, Fascicoli, Gestione pratiche |
| `admin` | amministratore | — | **solo** Uffici, Utenti (nessuna pratica) |

Cinque password sbagliate di fila per lo stesso utente lo bloccano per 15 minuti: per le prove sul blocco
usa un utente creato apposta (PER-11), non quelli qui sopra.

---

## 4. Documenti di prova

Tutti **inventati**. Da Windows si trovano in
`\\wsl.localhost\Ubuntu\home\lorenzo\applicazione-completa-esposti\docs\collaudo\dati\`
(si rigenerano con `scripts/genera-dati-collaudo.sh`).

| File | Cos'è | Con il finto motore |
|---|---|---|
| `C01_esposto_digitale.pdf` | PDF digitale: esposto per cani a Borgoverde, protocollo `0007101/2026` | lettura pulita |
| `C02_scansione_email_inoltrata.pdf` | scansione (solo immagine), 2 pagine: email della Polizia Locale **inoltrata** con il messaggio originale | lettura pulita |
| `C03_esposto_gatti.docx` | Word: colonia felina a Pievalta | lettura pulita |
| `C04_esposto_rumori.rtf` | RTF: rumori e odori da laboratorio a Castelrovo | lettura pulita |
| `C05_vuoto.pdf` | file vuoto (0 byte) | rifiutato dal server |
| `C06_danneggiato.pdf` | PDF danneggiato | lettura pulita (il finto non guarda il contenuto) |
| `C07_foto.jpg`, `C08_lettera.pages` | formati non ammessi | rifiutati dal modulo |
| `C09_riscontro_ats.pdf` | riscontro di ATS allo stesso protocollo `0007101/2026` | riscontro ATS |
| `F03_foglio_manoscritto.pdf` | scenario «manoscritto» | **lettura incerta** |
| `F04_errore_formato.pdf` | scenario «errore» | analisi non disponibile (`formato_non_supportato`), nessun nuovo tentativo |
| `F05_illeggibile.pdf` | scenario «illeggibile» | analisi non disponibile (`documento_illeggibile`) |
| `F06_scaduto.pdf` | scenario «scaduto» | tre tentativi, poi analisi non disponibile (`tempo_scaduto`) |
| `F07_instabile.pdf` | scenario «instabile» | errore al primo tentativo, riesce al secondo |
| `F08_occupato.pdf` | scenario «occupato» | motore occupato una volta, poi riesce |
| `F09_invalido.pdf` | scenario «invalido» | risultato fuori contratto, scartato: analisi non disponibile (`risultato_non_valido`) |

Per il **motore vero** si usano anche i documenti sintetici del motore (sulla workstation ATS):
`\\wsl.localhost\Ubuntu\home\lorenzo\classificatore-esposti-v2\tests\dati_sintetici\` — cartella `digitali\`
(`esposto_digitale.pdf`, `riscontro_word.docx`) e cartella `scansioni\` (`email_inoltrata.pdf`, `mano_1.pdf`,
`mano_2.pdf`, `mano_3.pdf`: gli ultimi tre sono **scritti a mano**).

---

## 5. Come registrare gli esiti e segnalare un problema

1. **Fai una copia personale** di questa pagina: `docs/collaudo/checklist-<nome>.md` (es. `checklist-syed.md`).
   Lavora sempre sulla copia.
2. Per ogni prova sostituisci `[ ]` con `[x]` sulla casella giusta e scrivi le note:
   - **OK**: il risultato è quello atteso;
   - **KO**: qualcosa è diverso → apri una issue (sotto) e scrivi il numero nelle note (es. `#12`);
   - **N/A**: la prova non si può fare (scrivi perché).
3. **Segnalazione**: su GitHub, repository `lorenzodegio/applicazione-completa-esposti` → *Issues* →
   *New issue* → **«Problema di collaudo»**. Il modello è anche in
   [modello-segnalazione.md](modello-segnalazione.md). Una issue per problema; se lo stesso problema
   compare in più prove, una sola issue con tutti i codici.
4. **Alla fine**: copia [esiti-modello.md](esiti-modello.md) in `docs/collaudo/esiti-<nome>.md`, compilalo
   (conteggi per area, elenco dei KO con le issue, impressioni generali) e consegnalo con un commit sul tuo
   ramo personale (Khalil: `khalil`; Syed: il ramo che gli indica Lorenzo).

---

## 6. Chi fa cosa

| Area | Codici | Prove | Chi |
|---|---|---|---|
| 1. Accesso | ACC-01…07 | 7 | Syed |
| 2. Permessi e sicurezza | PER-01…13 | 13 | **Khalil e Syed, separatamente** |
| 3. Caricamento | CAR-01…12 | 12 | Khalil |
| 4. Motore | MOT-01…16 | 16 | Khalil |
| 5. Smistamento | SMI-01…08 | 8 | Syed |
| 6. Inbox e valutazione | INB-01…10 | 10 | Syed |
| 7. Pratica e storico | PRA-01…11 | 11 | Syed |
| 8. Fascicoli e temi | FAS-01…07 | 7 | Syed |
| 9. Gestione pratiche e Home | GES-01…08 | 8 | Syed |
| 10. Registro delle azioni | REG-01…05 | 5 | Khalil |
| 11. Amministrazione | AMM-01…08 | 8 | Khalil |
| 12. Robustezza | ROB-01…07 | 7 | Khalil |
| 13. Privacy | PRI-01…05 | 5 | **Khalil e Syed, separatamente** |

Totale: **117 prove**. Khalil 66 (48 sue + 18 in comune), Syed 69 (51 sue + 18 in comune).
Le aree in comune si fanno **in modo indipendente**: ognuno le esegue da solo e registra il proprio esito,
senza confrontarsi prima.

Ordine consigliato: Syed parte da Accesso e Smistamento (per conoscere l'applicazione), Khalil da Caricamento
e Motore. Le prove col motore vero (MOT-10…16) vanno concordate per l'uso della workstation.

---

## 7. Le prove

Ogni prova indica il ruolo con cui entrare e il motore da usare. Se non è scritto altrimenti: ambiente
avviato con **DEMO=1 e finto motore** (2.2).

### Area 1 — Accesso (Syed)

#### ACC-01 — Ogni ruolo entra e vede solo il suo menu
Ruolo: `smistatore`, `op.vet`, `op.igp`, `admin` (uno alla volta)
1. Apri http://127.0.0.1:5173.
2. Accedi con `smistatore` / `password-sintetica-1` e annota le voci del menu a sinistra e il nome in basso.
3. Clicca **Esci** e ripeti con `op.vet`, `op.igp`, `admin`.

**Atteso:** i menu sono quelli della tabella in sezione 3; smistatore e operatori arrivano sulla **Home**,
l'amministratore su **Uffici**. In basso compaiono nome e ruolo dell'utente.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ACC-02 — Password errata
Ruolo: `op.vet`
1. Nella pagina di accesso scrivi `op.vet` e la password `sbagliata-123`, poi **Accedi**.

**Atteso:** messaggio «Credenziali non valide»; si resta sulla pagina di accesso; la password non compare
in chiaro da nessuna parte.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ACC-03 — Utente inesistente
1. Accedi con `utente.che.non.esiste` / `password-sintetica-1`.

**Atteso:** lo stesso messaggio di ACC-02 («Credenziali non valide»): la pagina non dice se l'utente esiste.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ACC-04 — Uscita
Ruolo: `op.vet`
1. Accedi, apri **Gestione pratiche**, poi clicca **Esci**.
2. Premi il tasto **Indietro** del browser.
3. Scrivi a mano l'indirizzo http://127.0.0.1:5173/pratiche.

**Atteso:** dopo **Esci** compare «Accedi al backoffice»; con **Indietro** e con l'indirizzo scritto a mano
non si vedono pratiche: si torna alla pagina di accesso.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ACC-05 — Sessione scaduta
Ruolo: `op.vet`
1. Accedi e apri **Inbox**.
2. Premi **F12** → scheda *Application* (in Edge: *Applicazione*) → *Cookies* → `http://127.0.0.1:5173` →
   seleziona il cookie **`esposti_sessione`** e cancellalo. Chiudi F12.
3. Clicca **Gestione pratiche**.

**Atteso:** si torna alla pagina «Accedi al backoffice» senza errori tecnici; dopo un nuovo accesso
l'applicazione funziona normalmente.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ACC-06 — Pagine interne senza accesso
1. In una finestra InPrivate/Incognito apri direttamente http://127.0.0.1:5173/inbox,
   poi http://127.0.0.1:5173/smistamento e http://127.0.0.1:5173/utenti.

**Atteso:** ogni volta compare la pagina di accesso; nessun dato visibile, nemmeno per un istante.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ACC-07 — Pagine di un altro ruolo
1. Con `op.vet` scrivi l'indirizzo http://127.0.0.1:5173/smistamento, poi http://127.0.0.1:5173/utenti.
2. Con `admin` scrivi http://127.0.0.1:5173/pratiche, poi http://127.0.0.1:5173/inbox.

**Atteso:** l'operatore viene riportato alla sua **Home**; l'amministratore alla pagina **Uffici**.
Nessuno vede, nemmeno per un istante, contenuti non suoi.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 2 — Permessi e sicurezza (Khalil e Syed, separatamente)

Prima di cominciare, con `smistatore` annota in un file di appunti:
- l'**id di una pratica di Medicina Veterinaria** (es. «Esposto cani via robinie_demo»: aprila da Gestione
  pratiche e copia l'ultima parte dell'indirizzo) e l'**id del suo documento** (scheda *Documenti*, link «Apri»);
- l'**id di una pratica di Igiene pubblica** (es. «Esposto rumori laboratorio_demo»).

#### PER-01 — L'operatore vede solo il suo ufficio
Ruolo: `op.igp`
1. Apri **Gestione pratiche** senza filtri e scorri tutte le pagine.
2. Apri **Inbox** e **Fascicoli**.

**Atteso:** compaiono **solo** pratiche di Igiene pubblica; nessuna di Medicina Veterinaria e nessuna
ancora da smistare. Lo stesso nell'Inbox e nei fascicoli.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-02 — Pratica di un altro ufficio scrivendo l'indirizzo
Ruolo: `op.igp`
1. Scrivi http://127.0.0.1:5173/pratiche/ seguito dall'id della pratica **di Veterinaria** annotato.
2. Prova anche http://127.0.0.1:5173/inbox/ seguito dallo stesso id.

**Atteso:** «Pratica non trovata» (non «vietato», non «accesso negato»): la pagina non lascia capire che
la pratica esiste. Nessun dato della pratica visibile.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-03 — Lo stesso nell'altro verso
Ruolo: `op.vet`
1. Scrivi http://127.0.0.1:5173/pratiche/ seguito dall'id della pratica **di Igiene pubblica**.

**Atteso:** «Pratica non trovata».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-04 — L'amministratore non vede pratiche
Ruolo: `admin`
1. Controlla il menu.
2. Scrivi http://127.0.0.1:5173/pratiche/ seguito da un id di pratica annotato.

**Atteso:** menu con solo **Uffici** e **Utenti**; l'indirizzo della pratica riporta a **Uffici** senza
mostrare nulla della pratica.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-05 — Lo smistatore vede tutto
Ruolo: `smistatore`
1. Apri **Gestione pratiche** senza filtri.
2. Apri le due pratiche annotate (Veterinaria e Igiene pubblica).

**Atteso:** compaiono pratiche di entrambi gli uffici e quelle da smistare; entrambe le pratiche si aprono.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-06 — Da `/docs`: pratica di un altro ufficio
Finestra InPrivate/Incognito su http://127.0.0.1:8100/docs, accesso come `op.igp` (sezione 2.5)
1. `GET /api/v1/pratiche/{pratica_id}` con l'id della pratica **di Veterinaria** → *Execute*.
2. `GET /api/v1/pratiche` → *Execute*.

**Atteso:** punto 1: risposta **404** con «Pratica non trovata». Punto 2: nell'elenco solo pratiche di
Igiene pubblica.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-07 — Da `/docs`: documenti di un altro ufficio
Come PER-06, accesso come `op.igp`
1. `GET /api/v1/documenti/{documento_id}/contenuto` con l'id del documento **di Veterinaria**.
2. `GET /api/v1/documenti/{documento_id}/testo` con lo stesso id.

**Atteso:** **404** in entrambi i casi; nessun contenuto del documento.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-08 — Da `/docs`: azioni di un ruolo diverso
Accesso come `op.vet` da `/docs`
1. `GET /api/v1/utenti` → *Execute*.
2. `POST /api/v1/pratiche/{pratica_id}/assegnazione` con l'id di una pratica di Veterinaria e corpo
   `{"versione": 1, "ufficio_id": "00000000-0000-0000-0000-000000000000"}`.
3. `GET /api/v1/smistamento`.

**Atteso:** **403** «Operazione non consentita al tuo ruolo» in tutti e tre i casi; nessuna modifica (la
pratica resta com'era nel backoffice).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-09 — Da `/docs`: l'amministratore e le pratiche
Accesso come `admin` da `/docs`
1. `GET /api/v1/pratiche`, poi `GET /api/v1/home`, poi `GET /api/v1/pratiche/{pratica_id}`.

**Atteso:** **403** per elenco e Home; per la singola pratica **403** o **404**, mai i dati della pratica.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-10 — Da `/docs`: senza accesso
1. In `/docs` esegui `POST /api/v1/auth/logout`, poi `GET /api/v1/pratiche` e `GET /api/v1/utenti`.

**Atteso:** **401** «Accesso richiesto» (o «Sessione non valida o scaduta»).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-11 — Blocco dopo troppi tentativi
Ruolo: `admin`, poi l'utente di prova
1. Con `admin` → **Utenti** → crea l'utente `collaudo.blocco.<tuo-nome>` (ruolo operatore, ufficio
   Medicina Veterinaria, password `prova-collaudo-1`).
2. Esci. Prova ad accedere con `collaudo.blocco.<tuo-nome>` e password sbagliata **5 volte**.
3. Al sesto tentativo usa la password **giusta**.

**Atteso:** i primi 5 tentativi danno «Credenziali non valide»; il sesto, anche con la password giusta,
dà «Troppi tentativi: riprova più tardi». Dopo circa 15 minuti l'accesso funziona (facoltativo).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-12 — Utente disattivato mentre è connesso
Due browser: nel primo `op.igp`, nel secondo `admin`
1. Nel primo browser accedi come `op.igp` e apri **Gestione pratiche**.
2. Nel secondo, come `admin` → **Utenti** → disattiva `op.igp`.
3. Torna al primo browser e clicca **Inbox**.
4. Prova ad accedere di nuovo come `op.igp`.
5. Come `admin` riattiva `op.igp` (serve alle altre prove).

**Atteso:** al punto 3 si torna alla pagina di accesso; al punto 4 «Credenziali non valide»; dopo la
riattivazione `op.igp` accede di nuovo.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PER-13 — Da `/docs`: modificare una pratica di un altro ufficio
Accesso come `op.vet` da `/docs`
1. `POST /api/v1/pratiche/{pratica_id}/note` con l'id della pratica **di Igiene pubblica** e corpo
   `{"testo": "nota di prova"}`.
2. `POST /api/v1/pratiche/{pratica_id}/restituzione` con lo stesso id e corpo
   `{"versione": 1, "motivo": "prova"}`.

**Atteso:** **404** in entrambi i casi; con `smistatore` nel backoffice la pratica non ha la nota e non è
cambiata.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 3 — Caricamento (Khalil)

Tutte le prove come `smistatore` → **Smistamento** → **«Carica un nuovo esposto»** (il riquadro si apre),
campo **«Documenti (anche più di uno)»**, pulsante **«Carica e analizza»**. File dalla sezione 4.

#### CAR-01 — PDF digitale
1. Scegli `C01_esposto_digitale.pdf` e clicca **Carica e analizza**.
2. Osserva la riga del documento sotto il pulsante.

**Atteso:** la riga mostra nome e dimensione, poi «Pratica ESP-… creata: il motore sta analizzando il
documento. Aprila» e uno stato che passa da *In coda per il motore* / *In analisi* ad **Analizzato**. La
pratica compare nell'elenco «Da smistare».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-02 — Scansione
1. Carica `C02_scansione_email_inoltrata.pdf`.
2. Apri la pratica (**Aprila**) → scheda **Documenti**.

**Atteso:** come CAR-01; il documento è in elenco e si apre con «Apri».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-03 — Word
1. Carica `C03_esposto_gatti.docx`.

**Atteso:** accettato, come CAR-01.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-04 — RTF
1. Carica `C04_esposto_rumori.rtf`.

**Atteso:** accettato, come CAR-01.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-05 — Formato non ammesso
1. Nella finestra di scelta dei file cambia il filtro in basso a destra in **«Tutti i file»** e scegli
   `C07_foto.jpg`.
2. Ripeti con `C08_lettera.pages`.

**Atteso:** messaggio «Formato non accettato: … Si caricano solo PDF, Word (.doc, .docx) e RTF.»; il
pulsante **Carica e analizza** resta disattivato; nessuna pratica creata. (Di norma la finestra di scelta
mostra solo PDF, Word e RTF.)

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-06 — File vuoto
1. Carica `C05_vuoto.pdf`.

**Atteso:** la riga mostra «Caricamento non riuscito: Il file «C05_vuoto.pdf» è vuoto» e lo stato
*Non caricato*; nessuna pratica creata (l'elenco «Da smistare» non cambia).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-07 — PDF danneggiato
1. Carica `C06_danneggiato.pdf`.
2. Apri la pratica → **Documenti** → **Apri**.

**Atteso:** il caricamento riesce (il controllo del contenuto lo fa il motore: vedi MOT-12); il file
scaricato con «Apri» è identico a quello caricato (stessa dimensione).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-08 — Più file: una pratica per ogni file
1. Scegli insieme `C01_esposto_digitale.pdf`, `C03_esposto_gatti.docx`, `C04_esposto_rumori.rtf`.
2. Controlla la scelta **«Come creare le pratiche»** e i campi Titolo/Protocollo/Comune.
3. Lascia **«Una pratica per ogni file (3 pratiche)»** e clicca **Carica e analizza**.

**Atteso:** è selezionato «Una pratica per ogni file»; Titolo, Protocollo e Comune sono disattivati con una
nota che lo spiega; compaiono **3 righe**, ognuna con la sua pratica, il suo link «Aprila» e il suo stato;
i file partono uno dopo l'altro; alla fine tre pratiche nuove in «Da smistare».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-09 — Più file: tutti in una pratica
1. Scegli insieme `C01_esposto_digitale.pdf` e `C09_riscontro_ats.pdf`.
2. Seleziona **«Tutti i file in una sola pratica»**, scrivi Titolo `Collaudo pratica doppia`, Protocollo
   `0007999/2026`, Comune `Borgoverde`; **Carica e analizza**.
3. Apri la pratica → **Riepilogo** e **Documenti**.

**Atteso:** due righe con **lo stesso** numero di pratica; una sola pratica nuova con titolo, protocollo e
comune scritti; nella scheda **Documenti** due documenti, il primo indicato come principale.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-10 — Avanzamento visibile
1. Premi **F12** → scheda *Network* (*Rete*) → menu della velocità → **«Slow 3G»** (o «3G lento»).
2. Carica `C02_scansione_email_inoltrata.pdf`.
3. Rimetti la velocità su **«No throttling»** (*Nessuna limitazione*) e chiudi F12.

**Atteso:** durante l'invio la riga mostra una barra di avanzamento e «Caricamento NN%» che cresce fino al
termine; poi *Caricato* e gli stati dell'analisi.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-11 — File troppo grande
1. In PowerShell crea un file da 60 MB:
   `$f=[IO.File]::Create("$env:TEMP\grande_collaudo.pdf"); $f.SetLength(60MB); $f.Close()`
2. Caricalo (si trova in `%TEMP%`). Alla fine cancellalo.

**Atteso:** «Caricamento non riuscito: Il file «grande_collaudo.pdf» supera 50 MB» (o «File troppo grande»);
nessuna pratica creata.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### CAR-12 — Titolo, protocollo e comune scritti a mano
1. Carica solo `C03_esposto_gatti.docx` con Titolo `Colonia felina di collaudo`, Protocollo `0007202/2026`,
   Comune `Pievalta`.
2. Apri la pratica.

**Atteso:** la pratica ha esattamente titolo, protocollo e comune scritti (l'analisi del motore non li
sovrascrive).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 4 — Motore (Khalil)

**Finto motore (MOT-01…09):** come `smistatore`, carica ogni file **da solo** (una pratica per file), poi
apri la pratica: **Riepilogo** (avvisi, proposta) e **Documenti** (stato dell'analisi, «Testo letto»). Il
finto motore restituisce sempre gli stessi esempi (stessi testi e lo stesso protocollo inventato
`0004512/2025` per molti documenti): è normale.

#### MOT-01 — Lettura pulita
1. Carica `C01_esposto_digitale.pdf`.

**Atteso:** *Analizzato*; nella pratica la **Proposta dell'IA** con esito, urgenza, «Perché», «Domanda
decisiva», «Frase del documento» e la scritta «Un suggerimento: decide sempre la persona.»; nessun
avviso di lettura incerta; stato *Da smistare*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-02 — Riscontro
1. Carica `C09_riscontro_ats.pdf`.

**Atteso:** *Analizzato*; nei «Dati della pratica» il tipo è **Riscontro ATS**.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-03 — Manoscritto, lettura incerta
1. Carica `F03_foglio_manoscritto.pdf`.
2. Apri la pratica → **Documenti** → **Testo letto**.

**Atteso:** avviso **«Lettura incerta.»** nella pratica; nella proposta l'elenco «Da verificare
sull'originale»; nel testo letto la pagina marcata come incerta.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-04 — Errore di formato
1. Carica `F04_errore_formato.pdf`.

**Atteso:** stato **«Analisi non disponibile (formato_non_supportato)»** dopo **un solo** tentativo;
nella pratica l'avviso «Analisi non disponibile.» e nessuna proposta; la pratica va comunque in
**Da smistare** (il lavoro delle persone non si blocca).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-05 — Documento illeggibile
1. Carica `F05_illeggibile.pdf`.

**Atteso:** «Analisi non disponibile (documento_illeggibile)», un solo tentativo, pratica in *Da smistare*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-06 — Tempo scaduto
1. Carica `F06_scaduto.pdf` e osserva la riga per circa un minuto.

**Atteso:** lo stato mostra nuovi tentativi (*In coda per il motore (tentativo 2)*, poi 3); alla fine
«Analisi non disponibile (tempo_scaduto)»; pratica in *Da smistare*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-07 — Instabile: riesce al secondo tentativo
1. Carica `F07_instabile.pdf`.

**Atteso:** dopo un primo errore, **Analizzato** al secondo tentativo; proposta presente.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-08 — Motore occupato
1. Carica `F08_occupato.pdf`.

**Atteso:** dopo una breve attesa, **Analizzato** (il motore occupato non conta come errore).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-09 — Risultato fuori contratto
1. Carica `F09_invalido.pdf`.

**Atteso:** «Analisi non disponibile (risultato_non_valido)», nessun nuovo tentativo, nessuna proposta
mostrata; pratica in *Da smistare*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

**Motore vero (MOT-10…16):** solo sulla workstation ATS, ambiente avviato come in 2.3, una persona alla
volta. Annota nelle note i **secondi** di ogni analisi (dall'avvio dell'analisi ad *Analizzato*).

#### MOT-10 — Il motore vero risponde
1. Apri http://127.0.0.1:8100/api/v1/salute.

**Atteso:** `"stato":"ok"`; nel motore `"stato":"ok"`, `"versione_motore":"2.2.0"`, `"versione_contratto":"1.2"`.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-11 — I documenti sintetici del motore
1. Carica, uno per pratica, i sei file di `classificatore-esposti-v2\tests\dati_sintetici\` (sezione 4).
2. Per ognuno apri la pratica: **Riepilogo** e **Documenti → Testo letto**.

**Atteso:** tutti **Analizzato**; testo letto pagina per pagina e fedele al documento; proposta con motivo
e domanda decisiva; voci della scheda con la loro frase; **lettura incerta solo sui tre scritti a mano**
(`mano_1`, `mano_2`, `mano_3`), non su PDF digitale, Word e scansione stampata. Tempi indicativi: digitale
e Word 20–30 s, scansione di 2 pagine circa 70 s, manoscritto 40–50 s.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-12 — I documenti di collaudo con il motore vero
1. Carica `C01`, `C02`, `C03`, `C04`, `C09` e `C06_danneggiato.pdf`, uno per pratica.

**Atteso:** C01–C04 e C09 **Analizzato**; per C01 e C09 il protocollo `0007101/2026` letto dal testo;
C02 riconosciuto come inoltro (email della Polizia Locale); C06 «Analisi non disponibile» con un codice
(per esempio `documento_illeggibile` o `formato_non_supportato`), senza bloccare la pratica.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-13 — Un documento alla volta
1. Carica insieme (una pratica per file) `mano_1.pdf`, `mano_2.pdf`, `mano_3.pdf`.

**Atteso:** un solo documento alla volta è *In analisi*, gli altri *In coda per il motore*; alla fine tutti
*Analizzato*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-14 — Motore spento durante l'analisi
1. Carica `C02_scansione_email_inoltrata.pdf`; quando la riga dice *In analisi*, in WSL:
   `cd ~/classificatore-esposti-v2 && docker compose stop motore`.
2. Aspetta un paio di minuti; apri http://127.0.0.1:8100/api/v1/salute.
3. Riaccendi: `docker compose up -d motore`; quando la salute torna `ok`, apri la pratica → **Documenti** →
   **Rianalizza**.

**Atteso:** punto 2: il documento finisce in «Analisi non disponibile (errore_interno)» dopo 3 tentativi,
la pratica va in *Da smistare*; la salute dice `"degradato"` con motore `irraggiungibile`. Punto 3: dopo
**Rianalizza** il documento arriva ad *Analizzato*. Mai bloccato per sempre su *In analisi*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-15 — Motore riavviato a metà
1. Carica `C02_scansione_email_inoltrata.pdf`; quando è *In analisi*:
   `cd ~/classificatore-esposti-v2 && docker compose restart motore`.
2. Osserva lo stato per qualche minuto.

**Atteso:** il motore perde il lavoro in corso e l'applicazione lo rimanda: il documento arriva ad
**Analizzato**, oppure, se il motore ci mette troppo a ripartire, ad «Analisi non disponibile
(errore_interno)», e in quel caso **Rianalizza** lo porta ad *Analizzato*. Annota quale dei due è successo.
Mai bloccato su *In analisi*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### MOT-16 — Rianalizzare un documento
1. Su una pratica già analizzata: **Documenti** → **Rianalizza**.
2. Apri **Note e registro**.

**Atteso:** lo stato torna *In coda* / *In analisi* e poi *Analizzato*; mentre è in corso non si può
rilanciare una seconda volta; nel registro compare «Analisi richiesta» con utente e ora, poi «Analisi completata».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 5 — Smistamento (Syed)

#### SMI-01 — Assegnare una pratica
Ruolo: `smistatore`, poi `op.vet`
1. **Smistamento** → nell'elenco «Da smistare» scegli «Esposto cane libero_demo» → **Assegna**.
2. Nella finestra «Assegna a un ufficio» scegli **Medicina Veterinaria** e conferma con **Assegna**.
3. Esci ed entra come `op.vet` → **Inbox**.

**Atteso:** la pratica sparisce da «Da smistare»; nella pratica lo stato è **Da validare** e l'ufficio
Medicina Veterinaria; `op.vet` la trova nella sua Inbox.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-02 — Riassegnare a un altro ufficio
Ruolo: `smistatore`, poi `op.igp`
1. Apri la pratica di SMI-01 (ora *Da validare*) → **Riassegna**.
2. Scegli **Igiene pubblica**, scrivi il motivo `prova di riassegnazione`, conferma.
3. Controlla come `op.vet` (Inbox) e come `op.igp` (Inbox).

**Atteso:** la pratica passa a Igiene pubblica, resta *Da validare*; sparisce dall'Inbox di `op.vet` e
compare in quella di `op.igp`; `op.vet` aprendo il vecchio indirizzo vede «Pratica non trovata».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-03 — Riassegnare senza motivo
Ruolo: `smistatore`
1. Su una pratica *Da validare* clicca **Riassegna**, scegli l'ufficio e **non** scrivere il motivo.

**Atteso:** il campo è indicato come «Motivo (obbligatorio)» e il pulsante **Riassegna** resta disattivato
finché il motivo è vuoto.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-04 — Non si riassegna una pratica già in lavorazione
Ruolo: `smistatore`
1. Apri una pratica *In lavorazione* (es. «Gatti in un'abitazione»).

**Atteso:** i pulsanti **Assegna a un ufficio** / **Riassegna** non ci sono.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-05 — Restituire allo smistatore
Ruolo: `op.vet`, poi `smistatore`
1. **Inbox** → apri una pratica → **Restituisci allo smistatore**.
2. Scrivi il motivo `non è di nostra competenza (prova)` → **Restituisci**.
3. Come `smistatore` apri **Smistamento**.

**Atteso:** la pratica sparisce dall'Inbox di `op.vet` e torna nell'elenco «Da smistare», senza ufficio;
nel percorso e nel registro c'è la restituzione con il motivo.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-06 — Restituire senza motivo
Ruolo: `op.vet`
1. **Inbox** → **Restituisci allo smistatore** e lascia vuoto «Perché la restituisci? (obbligatorio)».

**Atteso:** non si può confermare finché il motivo è vuoto.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-07 — Suggerimento dell'ufficio
Ruolo: `smistatore`
1. In **Smistamento**, per una pratica analizzata, cerca un ufficio suggerito.

**Atteso:** **funzione non ancora disponibile** (manca la tabella che collega l'ambito proposto all'ufficio).
Segna **N/A**. Controlla solo che l'elenco mostri la «Proposta: <esito>» del motore per le pratiche analizzate.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### SMI-08 — Lo smistatore non restituisce
Ruolo: `smistatore`
1. Apri una pratica *Da validare* dall'Inbox o da Gestione pratiche.

**Atteso:** il pulsante **Restituisci allo smistatore** non c'è (è un'azione dell'ufficio).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 6 — Inbox e valutazione (Syed)

#### INB-01 — Proposta accanto al modulo precompilato
Ruolo: `op.vet`
1. **Inbox** → «Esposto cani via robinie_demo».

**Atteso:** a sinistra la **Coda**; al centro la pratica; il riquadro **Proposta dell'IA** (esito, urgenza,
azione, «Perché», «Domanda decisiva», «Frase del documento», «Un suggerimento: decide sempre la persona.»)
accanto al modulo **La tua valutazione**, già compilato con gli stessi esito, urgenza e azione.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-02 — Avviso di lettura incerta
Ruolo: `op.vet`
1. **Inbox** → «Foglio manoscritto pollaio_demo».

**Atteso:** avviso ben visibile **«Lettura incerta.»** che invita a controllare l'originale; nella proposta
l'elenco «Da verificare sull'originale»; il link «Apri il PDF e lo storico» porta alla pratica.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-03 — Modificare e salvare la bozza
Ruolo: `op.vet`
1. In una pratica dell'Inbox cambia l'urgenza, aggiungi un'azione e scrivi una nota.
2. **Salva bozza**. Ricarica la pagina (F5).

**Atteso:** «Bozza salvata.»; dopo la ricarica i valori modificati ci sono ancora; la pratica resta *Da validare*.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-04 — Confermare senza esito o urgenza
Ruolo: `op.vet`
1. Togli la scelta di esito o urgenza (scegli una pratica senza proposta, es. «Colonia felina in cortile»)
   e prova a confermare.

**Atteso:** «Per confermare scegli esito e urgenza.»; la conferma non avviene.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-05 — Conferma e prossimo
Ruolo: `op.vet`
1. Su «Esposto cani via robinie_demo» **Conferma e vai al prossimo**.

**Atteso:** la pratica sparisce dalla Coda e si apre la successiva; aprendo la pratica confermata, stato
**In lavorazione** e valutazione con origine applicazione, autore `op.vet` e data.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-06 — Salvataggio contemporaneo da due browser
Due browser (Edge e Chrome, o normale e InPrivate), **entrambi** `op.vet`, sulla stessa pratica dell'Inbox
1. Nel browser A scegli urgenza **Alta** → **Salva bozza** («Bozza salvata.»).
2. Nel browser B, senza ricaricare, scegli urgenza **Immediata** → **Salva bozza**.
3. In B scegli di nuovo **Immediata** → **Salva bozza**.

**Atteso:** al punto 2 B riceve il messaggio che **un'altra persona ha salvato la valutazione** e il modulo si
ricarica con i dati di A (urgenza **Alta**); al punto 3 il salvataggio riesce. Nessun dato perso in silenzio.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-07 — Temi proposti, scartati e aggiunti
Ruolo: `op.vet`
1. In una pratica con tema proposto (es. «Cani», indicato «Proposto dall'IA») scarta il tema e aggiungine
   un altro con **Aggiungi un tema**.
2. **Conferma e vai al prossimo**; apri la pratica confermata.

**Atteso:** il modulo spiega che «I temi proposti dall'IA che non scarti vengono accettati con la conferma.»;
nella pratica confermata c'è solo il tema aggiunto, quello scartato no.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-08 — Disaccordo IA e operatore
Ruolo: `op.vet`
1. Su una pratica con proposta, cambia l'urgenza rispetto alla proposta e conferma.
2. Apri **Home** e poi **Gestione pratiche** con il filtro **«IA e operatore in disaccordo»**.

**Atteso:** la pratica compare nel riquadro «IA e operatore in disaccordo» della Home e nel filtro; nella
riga si vede la differenza (es. «IA: urgenza Normale, operatore: Alta»).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-09 — Coda vuota
Ruolo: `op.igp` (poche pratiche)
1. Conferma una dopo l'altra tutte le pratiche della sua Inbox.

**Atteso:** alla fine «Nessun esposto da validare. Ottimo lavoro.»; nessun errore.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### INB-10 — Dall'Inbox alla pratica e ritorno
Ruolo: `op.vet`
1. Nell'Inbox clicca **Apri il PDF e lo storico**.
2. Nella pratica clicca **Valida nella Inbox**.

**Atteso:** si apre la pratica giusta; il pulsante riporta all'Inbox sulla stessa pratica.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 7 — Pratica e storico (Syed)

#### PRA-01 — Percorso a pallini
Ruolo: `op.vet`
1. Apri una pratica confermata in INB-05 → scheda **Percorso**.

**Atteso:** pallini uniti da una linea: «Esposto ricevuto», «Proposta dell'IA», «Assegnata a Medicina
Veterinaria», «Validazione» **conclusi**; «Riscontro» **atteso** (pallino tratteggiato); la legenda spiega
concluso / in corso / atteso.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-02 — Documenti
Ruolo: `smistatore`
1. Apri la pratica di CAR-09 (due documenti) → **Documenti**.
2. **Apri** ciascun documento.

**Atteso:** elenco con nome, dimensione, stato dell'analisi; il principale indicato; «Apri» scarica o mostra
il file originale.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-03 — Testo pagina per pagina
Ruolo: `smistatore`
1. Carica `C02_scansione_email_inoltrata.pdf` (2 pagine) → apri la pratica → **Documenti** → **Testo letto**.

**Atteso:** finestra «Testo letto dal motore» con **Pagina 1** e **Pagina 2** separate e la modalità di
lettura per pagina. (Col finto motore il testo è di esempio; col motore vero è il testo del documento.)

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-04 — Frasi e pagine della scheda
Ruolo: `smistatore`
1. Apri una pratica analizzata → **Riepilogo**.

**Atteso:** per le voci proposte (ambito, problematica, elementi, comune, data) si vede la **frase del
documento** che le giustifica e la **pagina** da cui viene.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-05 — Note interne
Ruolo: `op.vet`
1. In una pratica dell'ufficio → **Note e registro** → scrivi una nota → **Aggiungi nota**.
2. Cerca un modo per modificarla o cancellarla.

**Atteso:** la nota compare con autore e data; non si può modificare né cancellare (una correzione è una
nuova nota); nel registro c'è «Nota aggiunta» **senza** il testo della nota.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-06 — Collegamento automatico per protocollo
Ruolo: `smistatore`
1. Carica `C01_esposto_digitale.pdf` con Protocollo `0007101/2026`; poi `C09_riscontro_ats.pdf` con lo
   stesso Protocollo (un file per volta).
2. Apri la prima → **Collegamenti**.

**Atteso:** in «Pratiche collegate» c'è l'altra pratica come **stesso protocollo**, creata automaticamente.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-07 — Collegamento manuale con tipo
Ruolo: `smistatore`
1. In una pratica → **Collegamenti** → **Collega un'altra pratica**: cerca per titolo o protocollo, scegli il
   **Tipo di collegamento**, scrivi una nota → **Collega**.
2. Poi **Rimuovi** il collegamento.

**Atteso:** il collegamento compare con il suo tipo (visto anche dall'altra pratica, nel verso giusto); dopo
**Rimuovi** sparisce dall'elenco ma resta nel registro.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-08 — Pratica collegata di un altro ufficio
Ruolo: `smistatore`, poi `op.vet`
1. Come `smistatore` collega una pratica di **Medicina Veterinaria** a una di **Igiene pubblica** (PRA-07).
2. Come `op.vet` apri la pratica di Veterinaria → **Collegamenti**.

**Atteso:** `op.vet` vede che la pratica collegata **esiste**, con **solo numero, ufficio e stato**; non
vede titolo né contenuto e non può aprirla (se ci prova: «Pratica non trovata»).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-09 — Azioni dell'ufficio
Ruolo: `op.vet`
1. Su una pratica *In lavorazione* → **Azioni** → **Aggiungi un'azione** (es. Sopralluogo, data prevista,
   descrizione) → **Aggiungi**.
2. Poi **Concludi** l'azione; guarda il **Percorso**.
3. Prova ad aggiungere un'azione su una pratica *Da validare*.

**Atteso:** l'azione compare prima prevista e poi conclusa; nel percorso c'è un pallino per l'azione; sulla
pratica *Da validare*: «Le azioni si aggiungono quando la pratica è in lavorazione.»

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-10 — Riscontro che arriva
Ruolo: `smistatore`, poi `op.vet`
1. Porta la pratica di `C01` (protocollo `0007101/2026`, PRA-06) fino a *In lavorazione* (assegna a
   Veterinaria, poi `op.vet` conferma).
2. Guarda il suo **Percorso** (passo «Riscontro»), con il riscontro `C09` caricato in PRA-06.

**Atteso:** il passo «Riscontro» è **concluso** perché esiste il riscontro ATS con lo stesso protocollo; in
una pratica senza riscontro lo stesso passo è **atteso**.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRA-11 — Chiudere e riaprire
Ruolo: `op.vet`, poi `smistatore`
1. `op.vet`: pratica *In lavorazione* → **Chiudi la pratica** → conferma.
2. `op.vet`: cerca un pulsante per riaprirla.
3. `smistatore`: apri la stessa pratica → **Riapri**: prova prima senza motivo, poi scrivi
   `riapertura di prova` e conferma.

**Atteso:** stato **Chiusa**; l'operatore non ha il pulsante per riaprire; lo smistatore sì, solo con il
motivo, e la pratica torna **In lavorazione**; nel registro «Stato cambiato» per chiusura e riapertura.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 8 — Fascicoli e temi (Syed)

#### FAS-01 — Elenco dei fascicoli
Ruolo: `op.vet`
1. Apri **Fascicoli**.

**Atteso:** un pulsante per ogni tema (Cani, Gatti e colonie feline, Animali da reddito, Avvelenamenti) con
il numero di pratiche con quel tema **confermato**; le pratiche con tema solo proposto non contano.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### FAS-02 — Un tema confermato entra nel fascicolo
Ruolo: `op.vet`
1. Annota il numero del fascicolo **Cani**.
2. Conferma nell'Inbox una pratica con tema «Cani» proposto, senza scartarlo.
3. Riapri **Fascicoli**.

**Atteso:** il fascicolo Cani ha una pratica in più ed è quella appena confermata.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### FAS-03 — Un tema scartato non entra
Ruolo: `op.vet`
1. Conferma una pratica scartando il tema proposto.

**Atteso:** la pratica non compare in quel fascicolo.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### FAS-04 — Tema aggiunto a mano
Ruolo: `op.vet`
1. Conferma una pratica aggiungendo il tema **Avvelenamenti**.

**Atteso:** compare nel fascicolo Avvelenamenti.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### FAS-05 — Ordine nel tempo
Ruolo: `op.vet`
1. Apri il fascicolo con più pratiche e guarda le date nel **Percorso del fascicolo**.

**Atteso:** pratiche **in ordine di tempo, dalla più vecchia alla più recente** (data del protocollo o, se
manca, data di arrivo).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### FAS-06 — Storico dal fascicolo
Ruolo: `op.vet`
1. Nel fascicolo clicca una pratica.

**Atteso:** a destra lo **Storico della pratica** a pallini, uguale al Percorso nella pratica; «Apri la
pratica» porta alla scheda.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### FAS-07 — Fascicoli e permessi
Ruolo: `op.igp`, poi `smistatore`
1. Confronta i numeri dei fascicoli tra `op.igp` e `smistatore`.

**Atteso:** `op.igp` conta solo le pratiche di Igiene pubblica; lo smistatore tutte.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 9 — Gestione pratiche e Home (Syed)

Consigliato partire da un ambiente appena azzerato (2.4).

#### GES-01 — Ricerca libera
Ruolo: `smistatore`
1. **Gestione pratiche** → «Protocollo, comune o parole»: cerca `0004512`, poi `Borgoverde`, poi `pollaio`.

**Atteso:** ogni ricerca mostra solo pratiche pertinenti (protocollo, comune o titolo); con un termine
inesistente: «Nessuna pratica con questi filtri.»

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-02 — Filtro per stato
Ruolo: `smistatore`
1. Filtra **Stato** = *Da validare*, poi *In lavorazione*, poi *Chiusa*.

**Atteso:** solo pratiche in quello stato; il numero di risultati cambia di conseguenza.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-03 — Filtro per fascicolo
Ruolo: `op.vet`
1. Filtra **Fascicolo** = *Cani*.

**Atteso:** le stesse pratiche del fascicolo Cani (area 8), solo dell'ufficio.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-04 — Filtro «IA e operatore in disaccordo»
Ruolo: `op.vet`
1. Spunta **IA e operatore in disaccordo**.

**Atteso:** solo le pratiche confermate con una valutazione diversa dalla proposta (es. quella di INB-08), con
la differenza scritta nella riga.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-05 — Filtro «Lettura incerta»
Ruolo: `smistatore`
1. Spunta **Lettura incerta**.

**Atteso:** solo pratiche con avviso di lettura incerta (es. i fogli manoscritti).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-06 — Filtro «Con valutazione ATS»
Ruolo: `smistatore`
1. Spunta **Con valutazione ATS**.

**Atteso:** nessuna pratica: l'importazione delle valutazioni già fatte da ATS **non è ancora disponibile**.
Se l'elenco è vuoto e senza errori, segna **OK**.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-07 — Numeri della Home coerenti
Ruolo: `op.vet`
1. Annota i numeri della **Home**: Da validare, In lavorazione, Lettura incerta, Senza riscontro, e il numero
   del riquadro «IA e operatore in disaccordo».
2. Confrontali con: le pratiche nell'**Inbox**; **Gestione pratiche** con Stato *In lavorazione*; con
   **Lettura incerta**; con **IA e operatore in disaccordo**.
3. Conferma una pratica dall'Inbox e ricontrolla la Home.

**Atteso:** i numeri coincidono con gli elenchi; dopo la conferma «Da validare» scende di uno e «In
lavorazione» sale di uno. «Senza riscontro» conta le pratiche in lavorazione senza riscontro collegato.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### GES-08 — Pagine dei risultati e indirizzo condivisibile
Ruolo: `smistatore`
1. In **Gestione pratiche** senza filtri, se c'è più di una pagina usa **Successiva** e **Precedente**.
2. Imposta un filtro, copia l'indirizzo dal browser e aprilo in un'altra scheda.

**Atteso:** le pagine scorrono senza ripetere pratiche; l'indirizzo copiato riapre la stessa ricerca con gli
stessi filtri.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 10 — Registro delle azioni (Khalil)

Il registro di una pratica è nella scheda **Note e registro** → «Registro delle azioni». Non c'è ancora una
pagina con il registro di tutto il sistema: per le azioni di amministrazione si usa il comando di REG-04.

#### REG-01 — Ogni azione sulla pratica lascia traccia
Ruolo: `smistatore`, poi `op.vet`
1. Su una pratica nuova: caricamento, assegnazione, salvataggio della bozza, conferma, nota, collegamento.
2. Apri **Note e registro**.

**Atteso:** una riga per ogni azione, in ordine, ognuna con **quando** (data e ora), **chi** (utente o
«sistema» per il motore) e **cosa**.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### REG-02 — Il registro non contiene testi liberi
1. Nella pratica di REG-01 confronta il registro con la nota e le note della valutazione scritte.

**Atteso:** il registro dice che una nota è stata aggiunta, ma **non** ne riporta il testo; lo stesso per i
testi liberi della valutazione.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### REG-03 — Aprire un documento lascia traccia
1. **Documenti** → **Apri** e **Testo letto**; poi **Note e registro**.

**Atteso:** nel registro «Documento aperto» e «Testo letto», con utente e ora.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### REG-04 — Azioni di amministrazione e accessi
1. Esegui AMM-02 e un accesso con password errata.
2. In WSL:
   `docker compose exec db psql -U esposti -c "select quando, azione, oggetto_tipo from registro_azioni order by id desc limit 15"`

**Atteso:** righe `utente.crea`, `accesso.fallito`, `accesso.riuscito` con l'ora; nessuna password e nessun
testo dei documenti.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### REG-05 — Il registro non si può cancellare
1. In WSL: `docker compose exec db psql -U esposti -c "delete from registro_azioni where id = (select max(id) from registro_azioni)"`

**Atteso:** errore «registro_azioni è di sola aggiunta»; nessuna riga cancellata.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 11 — Amministrazione (Khalil)

Tutte le prove come `admin` (pagine **Uffici** e **Utenti**).

#### AMM-01 — Creare un ufficio
1. **Uffici** → «Nuovo ufficio»: codice `COLL`, nome `Ufficio di collaudo` → **Crea ufficio**.
2. Ripeti con lo stesso codice.

**Atteso:** l'ufficio compare nell'elenco; il secondo tentativo dà «Esiste già un ufficio con questo codice».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-02 — Creare un operatore
1. **Utenti** → «Nuovo utente»: nome utente `op.collaudo`, nome e cognome `Operatore Collaudo`, ruolo
   operatore, ufficio **Ufficio di collaudo**, password `prova-collaudo-1` → **Crea utente**.
2. Esci e accedi come `op.collaudo`.

**Atteso:** accesso riuscito; menu da operatore; nessuna pratica (l'ufficio è nuovo).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-03 — Dati non validi
1. Crea un utente con un nome già esistente (es. `op.vet`).
2. Crea un utente con password di 9 caratteri.
3. Crea un operatore senza ufficio; poi uno smistatore con un ufficio.

**Atteso:** 1: «Esiste già un utente con questo nome»; 2: non accettata (almeno 10 caratteri); 3:
«Un operatore richiede un ufficio attivo» e «Solo gli operatori hanno un ufficio» (o il modulo non lo consente).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-04 — Reimpostare la password
1. **Utenti** → `op.collaudo` → **Reimposta password**: `nuova-password-1`.
2. Accedi come `op.collaudo` con la vecchia password, poi con la nuova.

**Atteso:** la vecchia non funziona, la nuova sì.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-05 — Disattivare un utente
1. Disattiva `op.collaudo` (spiega che «Le sessioni aperte dell'utente vengono chiuse.»).
2. Prova ad accedere come `op.collaudo`.

**Atteso:** nell'elenco risulta *Disattivato*; l'accesso dà «Credenziali non valide».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-06 — L'amministratore non si disattiva da solo
1. Prova a disattivare `admin` o a cambiargli il ruolo.

**Atteso:** «Non puoi disattivare te stesso né cambiare il tuo ruolo».

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-07 — Cambiare l'ufficio di un operatore
1. Riattiva `op.collaudo` e cambiagli l'ufficio in **Igiene pubblica**.
2. Accedi come `op.collaudo`.

**Atteso:** ora vede le pratiche di Igiene pubblica (come `op.igp`) e nessuna di Veterinaria.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### AMM-08 — Disattivare un ufficio
1. Disattiva **Ufficio di collaudo**.
2. Come `smistatore`, assegna una pratica: controlla l'elenco degli uffici.
3. Come `admin`, prova a creare un operatore in quell'ufficio.

**Atteso:** l'ufficio disattivato non compare tra quelli assegnabili; l'operatore non si crea («Un operatore
richiede un ufficio attivo»).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 12 — Robustezza (Khalil)

#### ROB-01 — Ricaricare durante il caricamento
Ruolo: `smistatore`
1. Rallenta la rete (CAR-10), carica insieme `C01`, `C03`, `C04` (una pratica per file) e premi **F5**
   mentre la barra avanza.
2. Rimetti la rete normale e guarda «Da smistare» e **Gestione pratiche**.

**Atteso:** nessun errore tecnico; le pratiche già create ci sono, complete del loro documento; quella
interrotta non c'è oppure c'è completa; **mai** una pratica senza documento.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ROB-02 — Ricaricare durante la valutazione
Ruolo: `op.vet`
1. Nell'Inbox modifica il modulo senza salvare e premi **F5**.

**Atteso:** il modulo torna all'ultimo stato salvato (bozza o proposta); nessun dato salvato a metà.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ROB-03 — Due schede dello stesso utente
Ruolo: `op.vet` in due schede dello stesso browser
1. Apri la stessa pratica dell'Inbox nelle due schede.
2. Nella prima **Conferma e vai al prossimo**; nella seconda prova a confermare.

**Atteso:** la seconda riceve un messaggio chiaro (la pratica è stata modificata nel frattempo o non è più
da validare) e non la conferma due volte; dopo la ricarica mostra lo stato aggiornato.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ROB-04 — Edge e Chrome
1. In **Edge** e in **Chrome**: accesso (ACC-01), caricamento di un file (CAR-01), conferma nell'Inbox
   (INB-05), percorso (PRA-01).

**Atteso:** stesso comportamento e aspetto nei due browser (carattere Titillium Web, colori, pulsanti).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ROB-05 — Finestra stretta
1. Restringi la finestra a circa 400 pixel di larghezza (o F12 → icona dispositivo mobile → 400 px).
2. Usa menu, Inbox, Gestione pratiche e Smistamento.

**Atteso:** tutto raggiungibile e leggibile; nessuno scorrimento orizzontale della pagina (le tabelle
possono scorrere da sole); pulsanti cliccabili.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ROB-06 — Tasto Indietro e link diretti
1. Naviga Home → Gestione pratiche (con un filtro) → una pratica → scheda Documenti, poi premi **Indietro**
   più volte.

**Atteso:** ogni passo indietro torna alla pagina precedente con i filtri e la scheda che avevi.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### ROB-07 — Riavvio dell'applicazione
1. In WSL: `docker compose restart`. Aspetta un minuto e ricarica il browser.

**Atteso:** dati e documenti ci sono ancora; l'utente è ancora connesso oppure deve solo riaccedere;
nessuna pratica bloccata *In analisi* (i lavori ripartono).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

### Area 13 — Privacy (Khalil e Syed, separatamente)

#### PRI-01 — Nessun testo dei documenti nei log dell'applicazione
1. Dopo aver caricato `C01_esposto_digitale.pdf`, in WSL:
   `docker compose logs api worker motore-finto | grep -iE "robinie|collaudi|anna esempio|C01_esposto"`

**Atteso:** **nessuna riga** (i log contengono solo identificativi, tempi e codici, mai testo o nomi di file).

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRI-02 — Nessun testo dei documenti nei log del motore vero
Solo workstation ATS, dopo MOT-12
1. `cd ~/classificatore-esposti-v2 && docker compose logs motore | grep -iE "collaudi|anna esempio|polizia locale|C0[1-9]_"`

**Atteso:** **nessuna riga**.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRI-03 — `/salute` non espone dettagli interni
1. Apri http://127.0.0.1:8100/api/v1/salute con il motore acceso e poi spento (MOT-14).

**Atteso:** solo stati e versioni; nessun indirizzo interno, nessun percorso di cartelle, nessun messaggio
d'errore tecnico.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRI-04 — Niente dati reali su GitHub
1. Sul repository GitHub guarda le issue aperte durante il collaudo e i file di `docs/collaudo/`.

**Atteso:** solo dati sintetici (nomi inventati, comuni Borgoverde/Castelrovo/Pievalta, indirizzi
`example.com`); screenshot senza nient'altro sullo schermo.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

#### PRI-05 — I documenti restano sulla macchina
1. In WSL: `docker volume ls | grep esposti` e `git status` nel repository.

**Atteso:** i documenti caricati stanno solo nei volumi Docker (`esposti-app_archivio`, `esposti-app_pgdata`);
`git status` non mostra file di documenti o di archivio da aggiungere.

Esito: [ ] OK  [ ] KO  [ ] N/A — Note:

---

Finite le prove: azzera l'ambiente (2.4), compila `docs/collaudo/esiti-<nome>.md` (sezione 5) e avvisa Lorenzo.
