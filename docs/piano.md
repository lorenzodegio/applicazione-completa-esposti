# Piano — Backoffice gestione esposti

Stato: **approvato** (versione 2.1). Tutte le proposte fatte finora sono
approvate; le questioni ancora aperte sono in fondo. Gli elenchi del modulo
ATS sono fissati (sezione 3.2).

Documenti collegati:
- [CLAUDE.md](../CLAUDE.md) — regole di lavoro
- [contratto_motore.md](contratto_motore.md) — interfaccia con il motore
- [consegna.md](consegna.md) — per chi arriva sul progetto
- [mockups/](mockups/) — le quattro schermate di riferimento
- [mockup.md](mockup.md) — il primo mockup HTML/JS

---

## 1. Principi

- **Permessi nel server.** Ogni lettura e scrittura passa da un unico filtro
  che decide cosa l'utente può vedere; il browser nasconde solo ciò che il
  server ha già negato. Ogni regola ha un test.
- **Pratica non visibile = pratica inesistente.** Fuori dal proprio perimetro
  l'API risponde `404`, non `403`. Unica eccezione: i *riferimenti* a pratiche
  collegate di altri uffici (numero, ufficio, stato; mai il contenuto).
- **L'IA propone, la persona decide.** La proposta del motore precompila e
  basta: valutazione, temi, ufficio e stato cambiano solo con un'azione di un
  utente, registrata.
- **Valutazione dell'operatore ≠ proposta dell'IA.** Sono due oggetti
  distinti, sempre confrontabili campo per campo.
- **SharePoint è l'archivio; la macchina elabora soltanto.** Sulla macchina
  i documenti esistono solo il tempo dell'elaborazione.
- **Registro di tutto**: chi, cosa, quando, su cosa.
- **Dati sintetici** in sviluppo; i dati reali (documenti, CSV di
  valutazioni ATS) non entrano mai nel repository, in chat o nei log.
- **Dipendenze dietro interfacce**: archivio, motore e accesso hanno
  un'implementazione locale/finta, sostituibile senza toccare il resto.

---

## 2. Flusso di una pratica

```
arrivo ──► IN_ANALISI ──► DA_SMISTARE ──► DA_VALIDARE ──► IN_LAVORAZIONE ──► CHIUSA
(caricamento   (motore,     (smistatore      (Inbox          (azioni,            (esito,
 o import da    un doc.      assegna un       dell'ufficio:   riscontro)          riscontro)
 cartella)      alla volta)  ufficio)         validazione)
                                  ▲                │                │
                                  └── restituita dall'ufficio ◄─────┘
```

- `IN_ANALISI`: documenti in archivio, lavori del motore in coda o in corso.
- `DA_SMISTARE`: analisi conclusa (o fallita) → **Smistamento**.
- `DA_VALIDARE`: assegnata a un ufficio → **Inbox** dell'ufficio
  (sostituisce `ASSEGNATA`, per coincidere con i mockup).
- `IN_LAVORAZIONE`: l'operatore ha confermato la valutazione e i temi.
- `CHIUSA`: conclusa. Riapertura solo dallo smistatore, con motivo.
  "Archiviata" e "Trasmessa" dei mockup sono **esiti**, non stati.

Le transizioni ammesse stanno in una tabella nel codice e sono testate.

---

## 3. Modello dei dati (PostgreSQL)

Chiavi `uuid` salvo dove indicato; date `timestamptz`. Migrazioni con Alembic.
**Nel database**: dati della pratica, scheda, proposta, valutazione, stati,
storico. **Nell'archivio** (SharePoint): documenti e testo estratto.

### 3.1 Organizzazione e accesso

**ufficio**: id, codice (unico), nome, attivo, creato_il. Gli uffici si
disattivano, non si cancellano.

**utente**
| campo | tipo | note |
|---|---|---|
| id | uuid | |
| username | text, unico | |
| nome_visualizzato | text | |
| email | text, null | |
| ruolo | enum `smistatore`, `operatore`, `amministratore` | un ruolo per utente |
| ufficio_id | uuid → ufficio, null | obbligatorio se operatore, vuoto altrimenti (CHECK) |
| password_hash | text, null | solo accesso locale (argon2) |
| provider | enum `locale`, `microsoft` | |
| id_esterno | text, null, unico | `oid` di Entra ID |
| attivo | bool | |
| ultimo_accesso | timestamptz, null | |

**sessione**: id (hash del token), utente_id, creata_il, scade_il, revocata.
Cookie `HttpOnly`, `Secure`, `SameSite=Strict`.

### 3.2 Vocabolari e temi

**voce_vocabolario**: id, vocabolario (`tipo_documento`, `esito`, `urgenza`,
`azione`, `ambito`, `problematica`, `elementi`), codice, etichetta, ordine,
attivo, `elenco` (`attuale` / `storico`), `converte_in` (→ voce attuale, per
le voci storiche).

Gli elenchi sono quelli del **modulo di valutazione ATS** (dettaglio e
valori nel [contratto, sezione 4](contratto_motore.md#4-vocabolari)):

| Vocabolario | Scelta | Valori |
|---|---|---|
| Ambito (attuale) | multipla | Medicina Veterinaria, Igiene pubblica, Disturbo/rumori, ARPA, Altro |
| Ambito (storico) | multipla | Veterinario, Igiene pubblica, Disturbo/rumori, Colonia felina, Allevamento/detenzione animali, Altro |
| Problematica | multipla | Maltrattamento animale, Abbandono animale, Condizioni igieniche carenti, Odori molesti, Rumori persistenti, Uccisione, Condizione di inidonea detenzione, Altro |
| Elementi | multipla | Ferite/sofferenza animale, Presenza escrementi, Odori molesti, Rumori persistenti, Rischio sanitario, Foto/allegati, Precedenti segnalazioni, Animali liberi o randagi, Omessa custodia, Altro |
| Esito | singola | Accolto, Archiviato, Da approfondire, Altro, Invio Modulo |
| Urgenza | singola | Bassa, Normale, Alta, Immediata |
| Azione | multipla | Sopralluogo, Sopralluogo congiunto, Contatto segnalante, Richiesta integrazione, Trasmissione ad altro ente |
| Tipo documento | singola | esposto, inoltro per competenza, richiesta ente, riscontro ATS, **lettera avvocato**, integrazione, altro |

**Conversione dell'ambito** (storico → attuale): Veterinario → Medicina
Veterinaria; Igiene pubblica → Igiene pubblica; Disturbo/rumori →
Disturbo/rumori; Colonia felina → Medicina Veterinaria;
Allevamento/detenzione animali → Medicina Veterinaria; Altro → Altro.
ARPA è nuovo. Il motore e il modulo dell'applicazione usano solo l'elenco
attuale; le valutazioni importate conservano il valore originale **e** quello
convertito, e confronti e filtri usano quello convertito. La distinzione tra
colonie feline e allevamenti resta nel **tema**.

**tema** (i fascicoli): id, codice, nome (es. *Cani*, *Gatti e colonie
feline*, *Animali da reddito*, *Avvelenamenti*), ordine, attivo.

**ambito_ufficio**: ambito → ufficio suggerito. Serve allo
smistatore: il motore propone l'ambito, l'applicazione ne ricava l'ufficio da
suggerire.

### 3.3 Pratica e documenti

**pratica**
| campo | tipo | note |
|---|---|---|
| id | uuid | |
| numero | text, unico | numero interno, es. `ESP-2026-000123` |
| protocollo | text, null, indicizzato | base dei collegamenti automatici |
| data_protocollo | date, null | |
| tipo | text | `tipo_documento` del documento principale (esposto, richiesta ente, riscontro ATS…) |
| titolo | text | breve, modificabile (es. "Pollaio a ridosso del confine") |
| comune | text, null | |
| canale | enum `caricamento_manuale`, `import_cartella` (poi `pec`, `protocollo`) | |
| stato | enum (sezione 2) | |
| ufficio_id | uuid → ufficio, null | **determina la visibilità per gli operatori** |
| documento_principale_id | uuid → documento, null | il suo risultato è la proposta della pratica |
| creata_il, aggiornata_il | timestamptz | |
| versione | int | blocco ottimistico (`409` se cambiata nel frattempo) |

**documento**
| campo | tipo | note |
|---|---|---|
| id | uuid | |
| pratica_id | uuid → pratica | |
| nome_file | text | nome originale; usato anche per abbinare le valutazioni ATS |
| tipo_mime, dimensione | | |
| sha256 | text | **impronta**, calcolata all'arrivo |
| archivio | enum `locale`, `sharepoint` | dove sta ora |
| id_archivio | text | **identificativo SharePoint** (o chiave locale) |
| id_archivio_testo | text, null | testo estratto, salvato **accanto** al documento |
| sha256_testo | text, null | |
| tipo_documento | text, null | confermato dall'operatore o dal risultato |
| caricato_da | uuid → utente, null | |
| caricato_il | timestamptz | |
| sostituito_da | uuid → documento, null | i documenti non si cancellano |

### 3.4 Motore

**lavoro_motore** (è anche la coda): id, documento_id, pratica_id, stato
(`in_coda`, `in_corso`, `completato`, `errore`), tentativi, richiesto_da
(null = automatico), richiesto_il, iniziato_il, finito_il, codice_errore.
Un lavoro = un documento. Il worker ne elabora **uno alla volta**
(`SELECT … FOR UPDATE SKIP LOCKED`, un solo worker).

**risultato_motore** (uno per lavoro completato; si mostra l'ultimo)
| campo | tipo | note |
|---|---|---|
| id | uuid | |
| lavoro_id, documento_id, pratica_id | uuid | |
| versione_motore, versione_contratto | text | |
| tipo_documento | text | con `tipo_documento_motivo` |
| protocollo_letto, data_protocollo_letta | null | |
| lettura_incerta | bool | genera l'avviso |
| pagine_incerte | int[] | per l'avviso e per l'anteprima |
| acquisizione | jsonb | modalità per pagina (`testo_nativo`, `ocr`, `ocr_manoscritto`, `nessuna`) |
| scheda | jsonb | voci con frase e pagina (forma del contratto) |
| proposta | jsonb | esito, urgenza, azione[], motivo, domanda_decisiva, da_verificare_sull_originale[] |
| temi_proposti | jsonb | tema, motivo, frase |
| ricevuto_il | timestamptz | |

Il **testo per pagina non sta nel database**: sta in archivio accanto al
documento (`<id_documento>.testo.json`).

### 3.5 Valutazione e temi della pratica

**valutazione** — *la valutazione dell'operatore*, una per pratica
| campo | tipo | note |
|---|---|---|
| id | uuid | |
| pratica_id | uuid, unico | |
| origine | enum `applicazione`, `import_ats` | |
| autore_id | uuid → utente, null | per `applicazione` |
| autore_nome | text, null | per `import_ats` (colonna *Operatore* del CSV) |
| compilata | bool | una valutazione compilata **non viene mai sovrascritta da un'importazione** |
| data_compilazione | date | |
| data_doc, comune | | |
| ambito, problematica, elementi | text[] | scelta multipla; ambito nell'elenco attuale |
| ambito_originale | text[], null | per `import_ats`: valori come scritti nel CSV (anche elenco storico) |
| ambito_altro, problematica_altro, elementi_altro | text, null | |
| esito, urgenza | text | |
| azione | text[] | scelta multipla |
| note | text, null | |
| da_risultato_id | uuid → risultato_motore, null | da quale proposta è partita la precompilazione |
| creata_il, aggiornata_il | | ogni modifica nel registro con prima/dopo |

**Disaccordo IA–operatore**: vista calcolata, vera se
tra valutazione compilata e proposta del documento principale differiscono
`esito`, `urgenza` o l'insieme di `azione`. I campi diversi si mostrano in
elenco (es. "IA: urgenza Immediata, operatore: Alta").

**pratica_tema**: pratica_id, tema_id, origine (`ia`, `operatore`), stato
(`proposto`, `confermato`, `scartato`), deciso_da, deciso_il. Il motore
propone, l'operatore conferma durante la validazione; può aggiungerne altri.

### 3.6 Lavorazione

**assegnazione** (storico): pratica_id, ufficio_id, ufficio_precedente_id,
assegnata_da, assegnata_il, motivo (obbligatorio per le riassegnazioni),
da_proposta_ia.

**cambio_stato**: pratica_id, da_stato, a_stato, utente_id, il, motivo.

**attivita** — le *azioni* dell'ufficio sulla pratica:
id, pratica_id, tipo (vocabolario `azione`), stato (`prevista`, `in_corso`,
`conclusa`, `annullata`), data_prevista, data_conclusione, descrizione,
creata_da.

**nota_interna**: pratica_id, autore_id, testo, creata_il. Non si modificano;
una correzione è una nuova nota.

### 3.7 Collegamenti

**tipo_collegamento**: codice, etichetta, etichetta_inversa (null =
simmetrico), manuale. Es. `DUPLICATO`, `INTEGRAZIONE`, `SEGUITO`, `CORRELATA`,
`RISCONTRO`, `STESSO_PROTOCOLLO` (solo automatico).

**collegamento** (solo manuali): pratica_da_id, pratica_a_id, tipo_id, nota,
creato_da/il, rimosso_da/il (rimozione logica).

I collegamenti **per stesso protocollo** non si salvano: si calcolano a ogni
lettura. Se la pratica collegata è di un altro ufficio, l'operatore ne vede
solo **numero, ufficio e stato**.

### 3.8 Percorso della pratica

Non è una tabella: è **calcolato** da documenti, risultati, assegnazioni,
valutazione, attività e collegamenti. Passi, in ordine:

| Passo | Da dove | Quando è "atteso" |
|---|---|---|
| Esposto | documento di tipo `esposto` | — |
| Inoltro | documento `inoltro_per_competenza` / `richiesta_ente` | non mostrato se assente |
| Proposta dell'IA | risultato del documento principale | durante `IN_ANALISI` (in corso) |
| Smistamento | prima assegnazione (e riassegnazioni) | finché `DA_SMISTARE` |
| Validazione | valutazione compilata | finché `DA_VALIDARE` |
| Azioni | una voce per `attivita` | prevista = atteso, in corso, conclusa |
| Riscontro | pratica collegata di tipo `riscontro_ats` con stesso protocollo | **atteso** finché non arriva |

Ogni passo: data, titolo, testo breve, eventuale link al documento e pagina,
stato `concluso` / `in_corso` / `atteso` (pallino pieno, contornato,
tratteggiato, come nel mockup).

### 3.9 Importazioni e registro

**importazione**: id, tipo (`cartella`, `valutazioni_ats`), avviata_da,
avviata_il, conclusa_il, **conteggi** (jsonb), esito. Mai nomi di file,
protocolli o contenuti: solo numeri.

**registro_azioni** (solo inserimento; niente UPDATE/DELETE nemmeno per
l'utente applicativo): id bigserial, quando, utente_id (null = sistema),
azione (es. `pratica.assegna`, `valutazione.conferma`, `documento.apri`,
`accesso.fallito`), oggetto_tipo, oggetto_id, pratica_id, dettagli (jsonb,
mai testo dei documenti), id_richiesta.

---

## 4. Documenti e archivio

SharePoint è l'**archivio di riferimento**. Sulla macchina si elabora soltanto.

1. **Arrivo**: il file va subito in archivio; nel database `id_archivio` e
   `sha256`.
2. **Elaborazione**: il worker scarica il file in una cartella temporanea
   del container, verifica l'impronta, lo invia al motore.
3. **Salvataggio**: il testo estratto va in archivio accanto al documento;
   scheda, proposta e temi nel database.
4. **Cancellazione**: la copia temporanea viene eliminata (anche in caso di
   errore); il worker conferma al motore (`DELETE /v1/analisi/{id}`) che può
   cancellare la sua.

```python
class ArchivioDocumenti(Protocol):
    def salva(self, pratica_id: UUID, nome_file: str, contenuto: BinaryIO) -> RiferimentoArchivio: ...  # id + sha256
    def salva_accanto(self, rif: RiferimentoArchivio, suffisso: str, contenuto: bytes) -> RiferimentoArchivio: ...
    def apri(self, rif: RiferimentoArchivio) -> BinaryIO: ...
    def impronta(self, rif: RiferimentoArchivio) -> str: ...
```

- `ArchivioCartellaLocale`: sviluppo e prima fase; radice da configurazione,
  fuori dal repository.
- `ArchivioSharePoint`: Microsoft Graph; struttura di siti/raccolte/cartelle
  ancora da definire.

**Migrazione** cartella locale → SharePoint: per ogni documento copia,
rilettura dell'impronta da SharePoint, confronto con `sha256`; **solo se
coincide** si aggiorna `archivio`/`id_archivio` e si cancella la copia locale.
Esito con soli conteggi (copiati, verificati, discordanti, saltati);
i discordanti restano in locale. Ripetibile senza danni.

---

## 5. Importazioni

### 5.1 Caricamento a mano
Lo smistatore crea una pratica dalla schermata Smistamento caricando uno o
più documenti (e il protocollo, se noto).

### 5.2 Importazione in blocco da cartella
Comando eseguito sulla macchina (comando, non pagina web, così nessun
percorso arriva dal browser):

```
python -m api.importa cartella <percorso> [--prova]
```

Ogni file diventa un documento; i file con lo stesso protocollo nel nome
finiscono nella stessa pratica *(da confermare: regola di raggruppamento)*.
Doppioni riconosciuti per `sha256`. `--prova` mostra solo i conteggi.

### 5.3 Valutazioni già fatte da ATS
Esiste un **CSV reale** con le valutazioni già compilate. **Non va mai aperto
in sviluppo, né letto da strumenti di assistenza, né copiato nel repository.**
I test usano un CSV sintetico con le stesse colonne
(`backend/api/tests/fixtures/valutazioni_ats_sintetiche.csv`).

Colonne: `File, Protocollo, Data doc, Comune, Operatore, Ambito, Ambito altro,
Problematica, Prob altro, Esito, Urgenza, Azione, Elementi, Elementi altro,
Note, Data comp, Compilato`. A scelta multipla: `Ambito`, `Problematica`,
`Azione`, `Elementi`.

```
python -m api.importa valutazioni-ats <file.csv> [--prova]
```

Regole:
1. Abbinamento **per nome del file** (`File` = `documento.nome_file`), poi,
   per le righe non abbinate, **per protocollo** (se porta a una sola pratica).
2. Una valutazione **compilata** esistente non viene **mai** sovrascritta.
3. Le righe abbinate creano una valutazione con `origine = import_ats`,
   `autore_nome = Operatore`, `data_compilazione = Data comp`.
4. Ambito nell'elenco storico → convertito nell'elenco attuale, conservando
   l'originale. Valori non presenti in nessun elenco → campo `_altro`
   corrispondente (e conteggiati come "non riconosciuti").
5. Output e registro: **solo conteggi** (righe lette, abbinate per file,
   abbinate per protocollo, ambigue, non abbinate, saltate perché già
   compilate, valori non riconosciuti). Mai righe, nomi o protocolli.

**Formato del CSV ancora aperto** (separatore, codifica, date, valori di
`Compilato`). Per le celle a scelta multipla, invece, la soluzione c'è già:
il motore contiene il codice che le **scompone qualunque sia il separatore**
(`cerchio1/voci.py` nel repository del motore). L'importazione **deve
riusare quella logica**, non riscriverne un'altra. Poiché il codice del
motore non si copia in questo repository, il riuso passa da una di queste
strade, da decidere con Khalil:
- *(preferita)* la logica di scomposizione viene pubblicata dal repository
  del motore come piccolo pacchetto Python versionato e installata qui come
  dipendenza con versione fissata;
- in alternativa, il motore espone una chiamata interna di scomposizione
  delle celle, descritta nel contratto.

In entrambi i casi questo repository ha test che verificano la scomposizione
su celle sintetiche.

Filtri conseguenti in Gestione pratiche: **con valutazione ATS**
(`origine = import_ats`) e **IA e operatore in disaccordo**.

---

## 6. Permessi

| Azione | smistatore | operatore | amministratore |
|---|---|---|---|
| Home, Fascicoli, Gestione pratiche | tutte le pratiche | solo `ufficio_id` = proprio | **no** |
| Smistamento (elenco `DA_SMISTARE`, assegna/riassegna) | sì | — | — |
| Creare pratica, caricare documenti | sì | sulle proprie (aggiunta documenti) | — |
| Inbox: validare, confermare temi | sì | sulle proprie | — |
| Restituire allo smistamento | — | sulle proprie, con motivo | — |
| Stati, attività, note | sì | sulle proprie | — |
| Collegamenti manuali | sì | tra pratiche che vede | — |
| Vedere pratica collegata di altro ufficio | tutta | solo numero, ufficio, stato | — |
| Rilanciare il motore su un documento | sì | sulle proprie | — |
| Uffici e utenti | — | — | sì |
| Importazioni (comandi sulla macchina) | — | — | — (chi ha accesso alla macchina) |

L'amministratore **non vede le pratiche** né il loro registro. Temi,
vocabolari e tipi di collegamento sono configurazione caricata con le
migrazioni.

Regole implementate come **un unico filtro di query**
(`pratiche_visibili(utente)`) riusato da tutti gli endpoint. Dopo una
riassegnazione l'ufficio precedente perde subito la visibilità.

**Test**: matrice parametrizzata ruolo × endpoint × (pratica del proprio
ufficio / di altro ufficio / non smistata) su PostgreSQL vero in Docker; test
delle transizioni; test che ogni scrittura produca una riga di registro; test
dell'importazione ATS sul CSV sintetico (abbinamenti, mai sovrascrivere,
solo conteggi).

---

## 7. API (FastAPI, prefisso `/api/v1`)

Elenchi paginati. Scritture su una pratica con `versione` → `409` se cambiata.
Ruoli: **S** smistatore, **O** operatore, **A** amministratore.

### Accesso
| Metodo | Percorso | Ruolo | Note |
|---|---|---|---|
| POST | `/auth/login` | pubblico | utente locale; limite di tentativi |
| POST | `/auth/logout` | tutti | |
| GET | `/auth/me` | tutti | utente, ruolo, ufficio, voci di menu |
| GET | `/auth/microsoft/login`, `/auth/microsoft/callback` | pubblico | fase 8 |

### Schermate
| Metodo | Percorso | Ruolo | Note |
|---|---|---|---|
| GET | `/home` | S, O | contatori (da validare, in lavorazione, lettura incerta, senza riscontro), ultimi arrivi, fascicoli più attivi, numero in disaccordo |
| GET | `/smistamento` | S | pratiche `DA_SMISTARE` con ufficio suggerito |
| GET | `/inbox` | S, O | coda `DA_VALIDARE` dell'ufficio, in ordine di arrivo |
| GET | `/fascicoli` | S, O | temi con numero di pratiche |
| GET | `/fascicoli/{tema}/pratiche` | S, O | pratiche con il tema confermato, in ordine di tempo |

### Pratiche
| Metodo | Percorso | Ruolo | Note |
|---|---|---|---|
| GET | `/pratiche` | S, O | filtri: testo (protocollo, comune, titolo), stato, tema, tipo, `con_valutazione_ats`, `disaccordo`, `lettura_incerta`, date |
| POST | `/pratiche` | S | multipart con documenti; accoda il motore |
| GET | `/pratiche/{id}` | S, O | dati, proposta, avviso, temi, valutazione |
| PATCH | `/pratiche/{id}` | S, O | titolo, protocollo, comune, documento principale |
| GET | `/pratiche/{id}/percorso` | S, O | passi calcolati (sezione 3.8) |
| POST | `/pratiche/{id}/assegnazione` | S | `{ufficio_id, motivo, da_proposta_ia}` → `DA_VALIDARE` |
| POST | `/pratiche/{id}/validazione` | S, O | valutazione + temi confermati → `IN_LAVORAZIONE` |
| POST | `/pratiche/{id}/restituzione` | O | `{motivo}` → `DA_SMISTARE` |
| POST | `/pratiche/{id}/stato` | S, O | transizioni ammesse |
| GET, PUT | `/pratiche/{id}/valutazione` | S, O | PUT rifiutato se origine `import_ats` compilata, salvo conferma esplicita |
| GET, POST, PATCH | `/pratiche/{id}/attivita`, `/attivita/{id}` | S, O | |
| GET, POST | `/pratiche/{id}/note` | S, O | |
| GET | `/pratiche/{id}/storico` | S, O | assegnazioni e stati |
| GET | `/pratiche/{id}/registro` | S, O | |

### Documenti e motore
| Metodo | Percorso | Ruolo | Note |
|---|---|---|---|
| GET, POST | `/pratiche/{id}/documenti` | S, O | |
| GET | `/documenti/{id}/contenuto` | S, O | passa dall'archivio; registra `documento.apri` |
| GET | `/documenti/{id}/testo` | S, O | testo per pagina, letto dall'archivio |
| GET | `/documenti/{id}/analisi` | S, O | risultati, ultimo per primo |
| POST | `/documenti/{id}/analisi` | S, O | rilancia: nuovo lavoro |
| GET | `/lavori/{id}` | S, O | stato del lavoro |

### Collegamenti
| Metodo | Percorso | Ruolo | Note |
|---|---|---|---|
| GET | `/pratiche/{id}/collegamenti` | S, O | automatici + manuali; per altri uffici solo numero, ufficio, stato |
| POST | `/pratiche/{id}/collegamenti` | S, O | `{pratica_id, tipo_id, nota}` |
| DELETE | `/collegamenti/{id}` | S, O | rimozione logica |
| GET | `/pratiche/ricerca-rapida?q=` | S, O | per scegliere la pratica da collegare |

### Configurazione e amministrazione
| Metodo | Percorso | Ruolo | Note |
|---|---|---|---|
| GET | `/vocabolari`, `/temi`, `/tipi-collegamento`, `/uffici` | S, O, A | sola lettura |
| POST, PATCH | `/uffici`, `/uffici/{id}` | A | |
| GET, POST, PATCH | `/utenti`, `/utenti/{id}` | A | ruolo, ufficio, attivazione |
| POST | `/utenti/{id}/password` | A | reimpostazione |
| GET | `/salute` | pubblico | database, archivio, coda, motore |

---

## 8. Schermate del backoffice

React + Vite + TypeScript. Riferimento visivo: [docs/mockups/](mockups/)
(struttura, testi, colori, carattere **Titillium Web**). I mockup sono file di
un editor di design: **riferimento, non codice da riusare**.

Colori principali dai mockup: menu `#17324D`, testo `#17324D`, sfondo
`#F3F5F7`, primario `#0059B3` (hover `#003F80`), bordi `#D5DCE3`, testo
secondario `#4A5B6B`, avviso `#FFF4E5` / bordo `#E0A458` / testo `#5C3300`,
riquadro IA `#EEF3F8`. Altezza minima dei controlli 44 px.

**Menu** (barra laterale): *Home*, *Inbox* (con contatore), *Fascicoli*,
*Gestione pratiche*; lo smistatore ha in più *Smistamento*. L'amministratore
vede solo *Uffici* e *Utenti*. In basso nome e ruolo dell'utente.

1. **Accesso** — utente e password; poi "Accedi con Microsoft".
2. **Home** (cruscotto) — `mockups/home`: quattro contatori (da validare, in
   lavorazione, lettura incerta, senza riscontro), "Arrivati per la
   validazione", "Fascicoli più attivi", riquadro "IA e operatore in
   disaccordo".
3. **Inbox** — `mockups/inbox`: coda a sinistra; al centro una pratica alla
   volta con protocollo, comune, fascicolo, collegamenti, avviso di lettura
   incerta; **proposta dell'IA** (voci, *Perché*, *Frase del documento*,
   domanda decisiva, cose da verificare) **accanto** al modulo **La tua
   valutazione** precompilato; conferma dei temi; "Conferma e vai al
   prossimo", "Restituisci allo smistatore"; apertura del PDF.
4. **Fascicoli** — `mockups/fascicolo`: temi come pulsanti con conteggio;
   percorso del fascicolo (pratiche in ordine di tempo); a destra il
   **percorso della pratica** selezionata a pallini e linee.
5. **Gestione pratiche** — `mockups/pratiche`: ricerca piatta (protocollo,
   comune o parole; stato; fascicolo; *con valutazione ATS*, *IA e operatore
   in disaccordo*, *lettura incerta*), tabella con protocollo, pratica, tipo,
   fascicolo, stato, esito (con nota di disaccordo), collegate.
6. **Dettaglio pratica** — pagina raggiungibile da tutte le schermate:
   documenti e testo estratto per pagina (con modalità di acquisizione),
   scheda con frasi, proposta, valutazione, temi, **percorso**, note,
   attività, collegamenti, registro.
7. **Smistamento** (solo smistatore) — pratiche `DA_SMISTARE` con ufficio
   suggerito e motivo; assegna/riassegna; nuova pratica con caricamento.
8. **Amministrazione** — Uffici, Utenti.

---

## 9. Servizi Docker (sviluppo)

`db` (PostgreSQL), `api`, `worker`, `motore-finto`, `backoffice` (Vite).
Il motore vero è un servizio separato, raggiunto con `MOTORE_URL`; nessun
volume condiviso con lui. Cartella temporanea del worker in un volume
effimero, svuotata a ogni lavoro.

---

## 10. Fasi

Ogni fase: lavoro sui rami `backend`/`frontend` (o personali), integrazione
in `dev`, test verdi prima del merge; `master` solo a fasi stabili.

| # | Fase | Contenuto | Fatto quando |
|---|---|---|---|
| 1 | **Server di base** | Compose; FastAPI, SQLAlchemy, Alembic; modello dati; accesso locale; filtro di visibilità; registro; uffici/utenti; vocabolari e temi; archivio su cartella locale; seed sintetico. Backoffice: scheletro, tema dai mockup, menu per ruolo, accesso, amministrazione | matrice dei permessi verde; ogni scrittura nel registro |
| 2 | **Smistatore** | Caricamento a mano; importazione da cartella; coda + worker + **motore finto**; Smistamento; assegnazione/riassegnazione | arrivo → analisi finta → assegnazione, con test |
| 3 | **Operatore** | Home; Inbox con validazione e temi; valutazione; restituzione; attività, stati, note; Gestione pratiche; dettaglio | un operatore non raggiunge pratiche di altri uffici, test inclusi |
| 4 | **Collegamenti e fascicoli** | Automatici per protocollo, manuali con tipo; riferimenti limitati per altri uffici; Fascicoli; percorso della pratica (riscontro atteso/concluso) | percorso corretto sui casi sintetici |
| 5 | **Aggancio del motore** | `MotoreHttp` secondo il [contratto](contratto_motore.md); test di contratto con il finto; tempi, errori, nuovi tentativi; cancellazione dei temporanei. **Può partire subito, in parallelo alle fasi 1–4** | stesse schermate con il motore vero su dati sintetici |
| 6 | **Valutazioni ATS** | Comando di importazione; filtri *con valutazione ATS* e *disaccordo*; riquadro in Home | test su CSV sintetico; sul reale solo conteggi |
| 7 | **SharePoint** | `ArchivioSharePoint`; testo accanto al documento; migrazione con verifica delle impronte | suite dell'archivio verde su entrambe le implementazioni |
| 8 | **Accesso Microsoft** | OIDC con Entra ID; abbinamento per `id_esterno`; ruoli dati dall'amministratore | accesso locale disattivabile da configurazione |

---

## 11. Questioni aperte

1. **Riuso della scomposizione delle celle** (`cerchio1/voci.py` del
   motore): pacchetto condiviso o chiamata del motore (sezione 5.3).
2. **Formato del CSV**: separatore, codifica, formato delle date, valori di
   `Compilato` (le celle multiple le scompone la logica del motore).
3. **Raggruppamento** nell'importazione da cartella: come capire quali file
   formano una stessa pratica.
4. **Stato** delle pratiche storiche abbinate dall'importazione ATS: restano
   nello stato attuale o vanno in `CHIUSA`?
5. **Ricerca nel testo estratto**: il testo sta in SharePoint; se serve la
   ricerca "per parole" anche nel contenuto, va deciso un indice.
6. **Struttura di SharePoint**: siti, raccolte, cartelle, permessi.
7. **Ruoli multipli** e operatori su più uffici.
8. **Conservazione** di documenti e registro, ed esportazione del registro.
