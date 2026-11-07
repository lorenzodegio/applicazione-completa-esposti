ESPOSTI DI PROVA PER AREA 2
vet: ee7a4e6d-5e83-427e-9bf5-26a77d6ccf89
igp: 45ad7824-9199-482f-b195-dbe1934b86e8


==========================================================================================================================================
==========================================================================================================================================


### Area 2 — Permessi e sicurezza (Khalil e Syed, separatamente)

#### PER-01 — L'operatore vede solo il suo ufficio
Ruolo: `op.igp`
1. Apri **Gestione pratiche** senza filtri e scorri tutte le pagine.
2. Apri **Inbox** e **Fascicoli**.

**Atteso:** compaiono **solo** pratiche di Igiene pubblica; nessuna di Medicina Veterinaria e nessuna
ancora da smistare. Lo stesso nell'Inbox e nei fascicoli.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-02 — Pratica di un altro ufficio scrivendo l'indirizzo
Ruolo: `op.igp`
1. Scrivi http://127.0.0.1:5173/pratiche/ seguito dall'id della pratica **di Veterinaria** annotato.
2. Prova anche http://127.0.0.1:5173/inbox/ seguito dallo stesso id.

**Atteso:** «Pratica non trovata» (non «vietato», non «accesso negato»): la pagina non lascia capire che
la pratica esiste. Nessun dato della pratica visibile.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-03 — Lo stesso nell'altro verso
Ruolo: `op.vet`
1. Scrivi http://127.0.0.1:5173/pratiche/ seguito dall'id della pratica **di Igiene pubblica**.

**Atteso:** «Pratica non trovata».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-04 — L'amministratore non vede pratiche
Ruolo: `admin`
1. Controlla il menu.
2. Scrivi http://127.0.0.1:5173/pratiche/ seguito da un id di pratica annotato.

**Atteso:** menu con solo **Uffici** e **Utenti**; l'indirizzo della pratica riporta a **Uffici** senza
mostrare nulla della pratica.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-05 — Lo smistatore vede tutto
Ruolo: `smistatore`
1. Apri **Gestione pratiche** senza filtri.
2. Apri le due pratiche annotate (Veterinaria e Igiene pubblica).

**Atteso:** compaiono pratiche di entrambi gli uffici e quelle da smistare; entrambe le pratiche si aprono.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-06 — Da `/docs`: pratica di un altro ufficio
Finestra InPrivate/Incognito su http://127.0.0.1:8100/docs, accesso come `op.igp` (sezione 2.5)
1. `GET /api/v1/pratiche/{pratica_id}` con l'id della pratica **di Veterinaria** → *Execute*.
2. `GET /api/v1/pratiche` → *Execute*.

**Atteso:** punto 1: risposta **404** con «Pratica non trovata». Punto 2: nell'elenco solo pratiche di
Igiene pubblica.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-07 — Da `/docs`: documenti di un altro ufficio
Come PER-06, accesso come `op.igp`
1. `GET /api/v1/documenti/{documento_id}/contenuto` con l'id del documento **di Veterinaria**.
2. `GET /api/v1/documenti/{documento_id}/testo` con lo stesso id.

**Atteso:** **404** in entrambi i casi; nessun contenuto del documento.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-08 — Da `/docs`: azioni di un ruolo diverso
Accesso come `op.vet` da `/docs`
1. `GET /api/v1/utenti` → *Execute*.
2. `POST /api/v1/pratiche/{pratica_id}/assegnazione` con l'id di una pratica di Veterinaria e corpo
   `{"versione": 1, "ufficio_id": "00000000-0000-0000-0000-000000000000"}`.
3. `GET /api/v1/smistamento`.

**Atteso:** **403** «Operazione non consentita al tuo ruolo» in tutti e tre i casi; nessuna modifica (la
pratica resta com'era nel backoffice).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-09 — Da `/docs`: l'amministratore e le pratiche
Accesso come `admin` da `/docs`
1. `GET /api/v1/pratiche`, poi `GET /api/v1/home`, poi `GET /api/v1/pratiche/{pratica_id}`.

**Atteso:** **403** per elenco e Home; per la singola pratica **403** o **404**, mai i dati della pratica.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-10 — Da `/docs`: senza accesso
1. In `/docs` esegui `POST /api/v1/auth/logout`, poi `GET /api/v1/pratiche` e `GET /api/v1/utenti`.

**Atteso:** **401** «Accesso richiesto» (o «Sessione non valida o scaduta»).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-11 — Blocco dopo troppi tentativi
Ruolo: `admin`, poi l'utente di prova
1. Con `admin` → **Utenti** → crea l'utente `collaudo.blocco.<tuo-nome>` (ruolo operatore, ufficio
   Medicina Veterinaria, password `prova-collaudo-1`).
2. Esci. Prova ad accedere con `collaudo.blocco.<tuo-nome>` e password sbagliata **5 volte**.
3. Al sesto tentativo usa la password **giusta**.

**Atteso:** i primi 5 tentativi danno «Credenziali non valide»; il sesto, anche con la password giusta,
dà «Troppi tentativi: riprova più tardi». Dopo circa 15 minuti l'accesso funziona (facoltativo).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-12 — Utente disattivato mentre è connesso
Due browser: nel primo `op.igp`, nel secondo `admin`
1. Nel primo browser accedi come `op.igp` e apri **Gestione pratiche**.
2. Nel secondo, come `admin` → **Utenti** → disattiva `op.igp`.
3. Torna al primo browser e clicca **Inbox**.
4. Prova ad accedere di nuovo come `op.igp`.
5. Come `admin` riattiva `op.igp` (serve alle altre prove).

**Atteso:** al punto 3 si torna alla pagina di accesso; al punto 4 «Credenziali non valide»; dopo la
riattivazione `op.igp` accede di nuovo.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PER-13 — Da `/docs`: modificare una pratica di un altro ufficio
Accesso come `op.vet` da `/docs`
1. `POST /api/v1/pratiche/{pratica_id}/note` con l'id della pratica **di Igiene pubblica** e corpo
   `{"testo": "nota di prova"}`.
2. `POST /api/v1/pratiche/{pratica_id}/restituzione` con lo stesso id e corpo
   `{"versione": 1, "motivo": "prova"}`.

**Atteso:** **404** in entrambi i casi; con `smistatore` nel backoffice la pratica non ha la nota e non è
cambiata.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:


==========================================================================================================================================
==========================================================================================================================================


### Area 3 — Caricamento (Khalil)

Tutte le prove come `smistatore` → **Smistamento** → **«Carica un nuovo esposto»** (il riquadro si apre),
campo **«Documenti (anche più di uno)»**, pulsante **«Carica e analizza»**. File dalla sezione 4.

#### CAR-01 — PDF digitale
1. Scegli `C01_esposto_digitale.pdf` e clicca **Carica e analizza**.
2. Osserva la riga del documento sotto il pulsante.

**Atteso:** la riga mostra nome e dimensione, poi «Pratica ESP-… creata: il motore sta analizzando il
documento. Aprila» e uno stato che passa da *In coda per il motore* / *In analisi* ad **Analizzato**. La
pratica compare nell'elenco «Da smistare».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-02 — Scansione
1. Carica `C02_scansione_email_inoltrata.pdf`.
2. Apri la pratica (**Aprila**) → scheda **Documenti**.

**Atteso:** come CAR-01; il documento è in elenco e si apre con «Apri».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-03 — Word
1. Carica `C03_esposto_gatti.docx`.

**Atteso:** accettato, come CAR-01.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-04 — RTF
1. Carica `C04_esposto_rumori.rtf`.

**Atteso:** accettato, come CAR-01.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-05 — Formato non ammesso
1. Nella finestra di scelta dei file cambia il filtro in basso a destra in **«Tutti i file»** e scegli
   `C07_foto.jpg`.
2. Ripeti con `C08_lettera.pages`.

**Atteso:** messaggio «Formato non accettato: … Si caricano solo PDF, Word (.doc, .docx) e RTF.»; il
pulsante **Carica e analizza** resta disattivato; nessuna pratica creata. (Di norma la finestra di scelta
mostra solo PDF, Word e RTF.)

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-06 — File vuoto
1. Carica `C05_vuoto.pdf`.

**Atteso:** la riga mostra «Caricamento non riuscito: Il file «C05_vuoto.pdf» è vuoto» e lo stato
*Non caricato*; nessuna pratica creata (l'elenco «Da smistare» non cambia).

Esito: [x] OK  [ ] KO  [ ] N/A — Note: Il messaggio di errore si sovrappone alla dimensione del file.

#### CAR-07 — PDF danneggiato
1. Carica `C06_danneggiato.pdf`.
2. Apri la pratica → **Documenti** → **Apri**.

**Atteso:** il caricamento riesce (il controllo del contenuto lo fa il motore: vedi MOT-12); il file
scaricato con «Apri» è identico a quello caricato (stessa dimensione).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-08 — Più file: una pratica per ogni file
1. Scegli insieme `C01_esposto_digitale.pdf`, `C03_esposto_gatti.docx`, `C04_esposto_rumori.rtf`.
2. Controlla la scelta **«Come creare le pratiche»** e i campi Titolo/Protocollo/Comune.
3. Lascia **«Una pratica per ogni file (3 pratiche)»** e clicca **Carica e analizza**.

**Atteso:** è selezionato «Una pratica per ogni file»; Titolo, Protocollo e Comune sono disattivati con una
nota che lo spiega; compaiono **3 righe**, ognuna con la sua pratica, il suo link «Aprila» e il suo stato;
i file partono uno dopo l'altro; alla fine tre pratiche nuove in «Da smistare».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-09 — Più file: tutti in una pratica
1. Scegli insieme `C01_esposto_digitale.pdf` e `C09_riscontro_ats.pdf`.
2. Seleziona **«Tutti i file in una sola pratica»**, scrivi Titolo `Collaudo pratica doppia`, Protocollo
   `0007999/2026`, Comune `Borgoverde`; **Carica e analizza**.
3. Apri la pratica → **Riepilogo** e **Documenti**.

**Atteso:** due righe con **lo stesso** numero di pratica; una sola pratica nuova con titolo, protocollo e
comune scritti; nella scheda **Documenti** due documenti, il primo indicato come principale.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-10 — Avanzamento visibile
1. Premi **F12** → scheda *Network* (*Rete*) → menu della velocità → **«Slow 3G»** (o «3G lento»).
2. Carica `C02_scansione_email_inoltrata.pdf`.
3. Rimetti la velocità su **«No throttling»** (*Nessuna limitazione*) e chiudi F12.

**Atteso:** durante l'invio la riga mostra una barra di avanzamento e «Caricamento NN%» che cresce fino al
termine; poi *Caricato* e gli stati dell'analisi.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:  

#### CAR-11 — File troppo grande
1. In PowerShell crea un file da 60 MB:
   `$f=[IO.File]::Create("$env:TEMP\grande_collaudo.pdf"); $f.SetLength(60MB); $f.Close()`
2. Caricalo (si trova in `%TEMP%`). Alla fine cancellalo.

**Atteso:** «Caricamento non riuscito: Il file «grande_collaudo.pdf» supera 50 MB» (o «File troppo grande»);
nessuna pratica creata.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### CAR-12 — Titolo, protocollo e comune scritti a mano
1. Carica solo `C03_esposto_gatti.docx` con Titolo `Colonia felina di collaudo`, Protocollo `0007202/2026`,
   Comune `Pievalta`.
2. Apri la pratica.

**Atteso:** la pratica ha esattamente titolo, protocollo e comune scritti (l'analisi del motore non li
sovrascrive).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:


==========================================================================================================================================
==========================================================================================================================================


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

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-02 — Riscontro
1. Carica `C09_riscontro_ats.pdf`.

**Atteso:** *Analizzato*; nei «Dati della pratica» il tipo è **Riscontro ATS**.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-03 — Manoscritto, lettura incerta
1. Carica `F03_foglio_manoscritto.pdf`.
2. Apri la pratica → **Documenti** → **Testo letto**.

**Atteso:** avviso **«Lettura incerta.»** nella pratica; nella proposta l'elenco «Da verificare
sull'originale»; nel testo letto la pagina marcata come incerta.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-04 — Errore di formato
1. Carica `F04_errore_formato.pdf`.

**Atteso:** stato **«Analisi non disponibile (formato_non_supportato)»** dopo **un solo** tentativo;
nella pratica l'avviso «Analisi non disponibile.» e nessuna proposta; la pratica va comunque in
**Da smistare** (il lavoro delle persone non si blocca).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-05 — Documento illeggibile
1. Carica `F05_illeggibile.pdf`.

**Atteso:** «Analisi non disponibile (documento_illeggibile)», un solo tentativo, pratica in *Da smistare*.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-06 — Tempo scaduto
1. Carica `F06_scaduto.pdf` e osserva la riga per circa un minuto.

**Atteso:** lo stato mostra nuovi tentativi (*In coda per il motore (tentativo 2)*, poi 3); alla fine
«Analisi non disponibile (tempo_scaduto)»; pratica in *Da smistare*.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-07 — Instabile: riesce al secondo tentativo
1. Carica `F07_instabile.pdf`.

**Atteso:** dopo un primo errore, **Analizzato** al secondo tentativo; proposta presente.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-08 — Motore occupato
1. Carica `F08_occupato.pdf`.

**Atteso:** dopo una breve attesa, **Analizzato** (il motore occupato non conta come errore).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-09 — Risultato fuori contratto
1. Carica `F09_invalido.pdf`.

**Atteso:** «Analisi non disponibile (risultato_non_valido)», nessun nuovo tentativo, nessuna proposta
mostrata; pratica in *Da smistare*.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

**Motore vero (MOT-10…16):** solo sulla workstation ATS, ambiente avviato come in 2.3, una persona alla
volta. Annota nelle note i **secondi** di ogni analisi (dall'avvio dell'analisi ad *Analizzato*).

#### MOT-10 — Il motore vero risponde
1. Apri http://127.0.0.1:8100/api/v1/salute.

**Atteso:** `"stato":"ok"`; nel motore `"stato":"ok"`, `"versione_motore":"2.2.0"`, `"versione_contratto":"1.2"`.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-11 — I documenti sintetici del motore
1. Carica, uno per pratica, i sei file di `classificatore-esposti-v2\tests\dati_sintetici\` (sezione 4).
2. Per ognuno apri la pratica: **Riepilogo** e **Documenti → Testo letto**.

**Atteso:** tutti **Analizzato**; testo letto pagina per pagina e fedele al documento; proposta con motivo
e domanda decisiva; voci della scheda con la loro frase; **lettura incerta solo sui tre scritti a mano**
(`mano_1`, `mano_2`, `mano_3`), non su PDF digitale, Word e scansione stampata. Tempi indicativi: digitale
e Word 20–30 s, scansione di 2 pagine circa 70 s, manoscritto 40–50 s.

Esito: [x] OK  [ ] KO  [ ] N/A — Note: digitale:36s, word:20s, manoscritto:(45s, 51s, 51s), scansione:1m 18s  

#### MOT-12 — I documenti di collaudo con il motore vero
1. Carica `C01`, `C02`, `C03`, `C04`, `C09` e `C06_danneggiato.pdf`, uno per pratica.

**Atteso:** C01–C04 e C09 **Analizzato**; per C01 e C09 il protocollo `0007101/2026` letto dal testo;
C02 riconosciuto come inoltro (email della Polizia Locale); C06 «Analisi non disponibile» con un codice
(per esempio `documento_illeggibile` o `formato_non_supportato`), senza bloccare la pratica.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-13 — Un documento alla volta
1. Carica insieme (una pratica per file) `mano_1.pdf`, `mano_2.pdf`, `mano_3.pdf`.

**Atteso:** un solo documento alla volta è *In analisi*, gli altri *In coda per il motore*; alla fine tutti
*Analizzato*.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-14 — Motore spento durante l'analisi
1. Carica `C02_scansione_email_inoltrata.pdf`; quando la riga dice *In analisi*, in WSL:
   `cd ~/classificatore-esposti-v2 && docker compose stop motore`.
2. Aspetta un paio di minuti; apri http://127.0.0.1:8100/api/v1/salute.
3. Riaccendi: `docker compose up -d motore`; quando la salute torna `ok`, apri la pratica → **Documenti** →
   **Rianalizza**.

**Atteso:** punto 2: il documento finisce in «Analisi non disponibile (errore_interno)» dopo 3 tentativi,
la pratica va in *Da smistare*; la salute dice `"degradato"` con motore `irraggiungibile`. Punto 3: dopo
**Rianalizza** il documento arriva ad *Analizzato*. Mai bloccato per sempre su *In analisi*.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### MOT-15 — Motore riavviato a metà
1. Carica `C02_scansione_email_inoltrata.pdf`; quando è *In analisi*:
   `cd ~/classificatore-esposti-v2 && docker compose restart motore`.
2. Osserva lo stato per qualche minuto.

**Atteso:** il motore perde il lavoro in corso e l'applicazione lo rimanda: il documento arriva ad
**Analizzato**, oppure, se il motore ci mette troppo a ripartire, ad «Analisi non disponibile
(errore_interno)», e in quel caso **Rianalizza** lo porta ad *Analizzato*. Annota quale dei due è successo.
Mai bloccato su *In analisi*.

Esito: [x] OK  [ ] KO  [ ] N/A — Note: stato rilevato:Analisi non disponibile (errore_interno)

#### MOT-16 — Rianalizzare un documento
1. Su una pratica già analizzata: **Documenti** → **Rianalizza**.
2. Apri **Note e registro**.

**Atteso:** lo stato torna *In coda* / *In analisi* e poi *Analizzato*; mentre è in corso non si può
rilanciare una seconda volta; nel registro compare «Analisi richiesta» con utente e ora, poi «Analisi completata».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:


==========================================================================================================================================
==========================================================================================================================================


### Area 10 — Registro delle azioni (Khalil)

Il registro di una pratica è nella scheda **Note e registro** → «Registro delle azioni». Non c'è ancora una
pagina con il registro di tutto il sistema: per le azioni di amministrazione si usa il comando di REG-04.

#### REG-01 — Ogni azione sulla pratica lascia traccia
Ruolo: `smistatore`, poi `op.vet`
1. Su una pratica nuova: caricamento, assegnazione, salvataggio della bozza, conferma, nota, collegamento.
2. Apri **Note e registro**.

**Atteso:** una riga per ogni azione, in ordine, ognuna con **quando** (data e ora), **chi** (utente o
«sistema» per il motore) e **cosa**.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### REG-02 — Il registro non contiene testi liberi
1. Nella pratica di REG-01 confronta il registro con la nota e le note della valutazione scritte.

**Atteso:** il registro dice che una nota è stata aggiunta, ma **non** ne riporta il testo; lo stesso per i
testi liberi della valutazione.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### REG-03 — Aprire un documento lascia traccia
1. **Documenti** → **Apri** e **Testo letto**; poi **Note e registro**.

**Atteso:** nel registro «Documento aperto» e «Testo letto», con utente e ora.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### REG-04 — Azioni di amministrazione e accessi
1. Esegui AMM-02 e un accesso con password errata.
2. In WSL:
   `docker compose exec db psql -U esposti -c "select quando, azione, oggetto_tipo from registro_azioni order by id desc limit 15"`

**Atteso:** righe `utente.crea`, `accesso.fallito`, `accesso.riuscito` con l'ora; nessuna password e nessun
testo dei documenti.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### REG-05 — Il registro non si può cancellare
1. In WSL: `docker compose exec db psql -U esposti -c "delete from registro_azioni where id = (select max(id) from registro_azioni)"`

**Atteso:** errore «registro_azioni è di sola aggiunta»; nessuna riga cancellata.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:


==========================================================================================================================================
==========================================================================================================================================


### Area 11 — Amministrazione (Khalil)

Tutte le prove come `admin` (pagine **Uffici** e **Utenti**).

#### AMM-01 — Creare un ufficio
1. **Uffici** → «Nuovo ufficio»: codice `COLL`, nome `Ufficio di collaudo` → **Crea ufficio**.
2. Ripeti con lo stesso codice.

**Atteso:** l'ufficio compare nell'elenco; il secondo tentativo dà «Esiste già un ufficio con questo codice».

Esito: [x] OK  [ ] KO  [ ] N/A — Note: 

#### AMM-02 — Creare un operatore
1. **Utenti** → «Nuovo utente»: nome utente `op.collaudo`, nome e cognome `Operatore Collaudo`, ruolo
   operatore, ufficio **Ufficio di collaudo**, password `prova-collaudo-1` → **Crea utente**.
2. Esci e accedi come `op.collaudo`.

**Atteso:** accesso riuscito; menu da operatore; nessuna pratica (l'ufficio è nuovo).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### AMM-03 — Dati non validi
1. Crea un utente con un nome già esistente (es. `op.vet`).
2. Crea un utente con password di 9 caratteri.
3. Crea un operatore senza ufficio; poi uno smistatore con un ufficio.	

**Atteso:** 1: «Esiste già un utente con questo nome»; 2: non accettata (almeno 10 caratteri); 3:
«Un operatore richiede un ufficio attivo» e «Solo gli operatori hanno un ufficio» (o il modulo non lo consente).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### AMM-04 — Reimpostare la password
1. **Utenti** → `op.collaudo` → **Reimposta password**: `nuova-password-1`.
2. Accedi come `op.collaudo` con la vecchia password, poi con la nuova.

**Atteso:** la vecchia non funziona, la nuova sì.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### AMM-05 — Disattivare un utente
1. Disattiva `op.collaudo` (spiega che «Le sessioni aperte dell'utente vengono chiuse.»).
2. Prova ad accedere come `op.collaudo`.

**Atteso:** nell'elenco risulta *Disattivato*; l'accesso dà «Credenziali non valide».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### AMM-06 — L'amministratore non si disattiva da solo
1. Prova a disattivare `admin` o a cambiargli il ruolo.

**Atteso:** «Non puoi disattivare te stesso né cambiare il tuo ruolo».

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### AMM-07 — Cambiare l'ufficio di un operatore
1. Riattiva `op.collaudo` e cambiagli l'ufficio in **Igiene pubblica**.
2. Accedi come `op.collaudo`.

**Atteso:** ora vede le pratiche di Igiene pubblica (come `op.igp`) e nessuna di Veterinaria.

Esito: [ ] OK  [x] KO  [ ] N/A — Note: #1

#### AMM-08 — Disattivare un ufficio
1. Disattiva **Ufficio di collaudo**.
2. Come `smistatore`, assegna una pratica: controlla l'elenco degli uffici.
3. Come `admin`, prova a creare un operatore in quell'ufficio.

**Atteso:** l'ufficio disattivato non compare tra quelli assegnabili; l'operatore non si crea («Un operatore
richiede un ufficio attivo»).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:


==========================================================================================================================================
==========================================================================================================================================


### Area 12 — Robustezza (Khalil)

#### ROB-01 — Ricaricare durante il caricamento
Ruolo: `smistatore`
1. Rallenta la rete (CAR-10), carica insieme `C01`, `C03`, `C04` (una pratica per file) e premi **F5**
   mentre la barra avanza.
2. Rimetti la rete normale e guarda «Da smistare» e **Gestione pratiche**.

**Atteso:** nessun errore tecnico; le pratiche già create ci sono, complete del loro documento; quella
interrotta non c'è oppure c'è completa; **mai** una pratica senza documento.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### ROB-02 — Ricaricare durante la valutazione
Ruolo: `op.vet`
1. Nell'Inbox modifica il modulo senza salvare e premi **F5**.

**Atteso:** il modulo torna all'ultimo stato salvato (bozza o proposta); nessun dato salvato a metà.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### ROB-03 — Due schede dello stesso utente
Ruolo: `op.vet` in due schede dello stesso browser
1. Apri la stessa pratica dell'Inbox nelle due schede.
2. Nella prima **Conferma e vai al prossimo**; nella seconda prova a confermare.

**Atteso:** la seconda riceve un messaggio chiaro (la pratica è stata modificata nel frattempo o non è più
da validare) e non la conferma due volte; dopo la ricarica mostra lo stato aggiornato.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### ROB-04 — Edge e Chrome
1. In **Edge** e in **Chrome**: accesso (ACC-01), caricamento di un file (CAR-01), conferma nell'Inbox
   (INB-05), percorso (PRA-01).

**Atteso:** stesso comportamento e aspetto nei due browser (carattere Titillium Web, colori, pulsanti).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### ROB-05 — Finestra stretta
1. Restringi la finestra a circa 400 pixel di larghezza (o F12 → icona dispositivo mobile → 400 px).
2. Usa menu, Inbox, Gestione pratiche e Smistamento.

**Atteso:** tutto raggiungibile e leggibile; nessuno scorrimento orizzontale della pagina (le tabelle
possono scorrere da sole); pulsanti cliccabili.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### ROB-06 — Tasto Indietro e link diretti
1. Naviga Home → Gestione pratiche (con un filtro) → una pratica → scheda Documenti, poi premi **Indietro**
   più volte.

**Atteso:** ogni passo indietro torna alla pagina precedente con i filtri e la scheda che avevi.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### ROB-07 — Riavvio dell'applicazione
1. In WSL: `docker compose restart`. Aspetta un minuto e ricarica il browser.

**Atteso:** dati e documenti ci sono ancora; l'utente è ancora connesso oppure deve solo riaccedere;
nessuna pratica bloccata *In analisi* (i lavori ripartono).

Esito: [x] OK  [ ] KO  [ ] N/A — Note: Rimane connesso


==========================================================================================================================================
==========================================================================================================================================


### Area 13 — Privacy (Khalil e Syed, separatamente)

#### PRI-01 — Nessun testo dei documenti nei log dell'applicazione
1. Dopo aver caricato `C01_esposto_digitale.pdf`, in WSL:
   `docker compose logs api worker motore-finto | grep -iE "robinie|collaudi|anna esempio|C01_esposto"`

**Atteso:** **nessuna riga** (i log contengono solo identificativi, tempi e codici, mai testo o nomi di file).

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PRI-02 — Nessun testo dei documenti nei log del motore vero
Solo workstation ATS, dopo MOT-12
1. `cd ~/classificatore-esposti-v2 && docker compose logs motore | grep -iE "collaudi|anna esempio|polizia locale|C0[1-9]_"`

**Atteso:** **nessuna riga**.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PRI-03 — `/salute` non espone dettagli interni
1. Apri http://127.0.0.1:8100/api/v1/salute con il motore acceso e poi spento (MOT-14).

**Atteso:** solo stati e versioni; nessun indirizzo interno, nessun percorso di cartelle, nessun messaggio
d'errore tecnico.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PRI-04 — Niente dati reali su GitHub
1. Sul repository GitHub guarda le issue aperte durante il collaudo e i file di `docs/collaudo/`.

**Atteso:** solo dati sintetici (nomi inventati, comuni Borgoverde/Castelrovo/Pievalta, indirizzi
`example.com`); screenshot senza nient'altro sullo schermo.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:

#### PRI-05 — I documenti restano sulla macchina
1. In WSL: `docker volume ls | grep esposti` e `git status` nel repository.

**Atteso:** i documenti caricati stanno solo nei volumi Docker (`esposti-app_archivio`, `esposti-app_pgdata`);
`git status` non mostra file di documenti o di archivio da aggiungere.

Esito: [x] OK  [ ] KO  [ ] N/A — Note:
