# Contratto del motore — versione 1.0

Questo documento definisce **l'unico punto di contatto** tra l'applicazione
(questo repository) e il motore di classificazione (`classificatore-esposti-v2`,
repository separato). Nessuna delle due parti legge file, cartelle o database
dell'altra: si scambiano solo i messaggi descritti qui.

Tutti gli esempi sono **sintetici** (comuni, persone, protocolli inventati).

---

## 1. Ruoli

| Parte | Responsabilità |
|---|---|
| **Applicazione** (`backend/motore`, worker) | tiene la coda dei lavori; prende **un lavoro alla volta**; scarica il documento dall'archivio in una cartella temporanea; lo invia al motore; salva il risultato; cancella la copia temporanea |
| **Motore** (servizio Docker separato) | riceve un documento, lo analizza, restituisce il risultato; **non conserva** il documento né il testo dopo la consegna del risultato; non scrive contenuti dei documenti nei log |

L'unità di lavoro è **un documento**. Una pratica con tre documenti genera tre
lavori. Il risultato della pratica è quello del suo *documento principale*
(vedi [piano](piano.md)).

---

## 2. Trasporto

HTTP/JSON tra due servizi della stessa rete Docker. URL di base da
configurazione (`MOTORE_URL`, es. `http://motore:8080`). Il motore non è
esposto fuori dalla rete interna.

Il modello è **asincrono**: l'analisi (soprattutto OCR di fogli scritti a
mano) può durare minuti.

| Metodo | Percorso | Scopo |
|---|---|---|
| `GET` | `/v1/salute` | stato, versione del motore e del contratto |
| `POST` | `/v1/analisi` | consegna un documento; risponde `202` con l'id del lavoro |
| `GET` | `/v1/analisi/{id_lavoro}` | stato del lavoro e, se concluso, risultato |
| `DELETE` | `/v1/analisi/{id_lavoro}` | l'applicazione conferma di aver salvato il risultato: il motore cancella tutto ciò che resta del lavoro |

**Uno alla volta**: l'applicazione non invia un nuovo lavoro finché il
precedente non è concluso. Se il motore riceve un lavoro mentre è occupato
risponde `429` con `Retry-After`; l'applicazione riprova più tardi.

### 2.1 `GET /v1/salute`

```json
{
  "stato": "pronto",
  "versione_motore": "2.3.0",
  "versione_contratto": "1.0",
  "occupato": false
}
```

### 2.2 `POST /v1/analisi`

`multipart/form-data` con due parti:

- `documento`: il file (PDF, immagine, `.eml`, `.docx`…);
- `metadati`: JSON

```json
{
  "versione_contratto": "1.0",
  "id_lavoro": "6f1c2a0e-8b7d-4d5e-9a31-0c2b9e4f7a10",
  "documento": {
    "id": "d2b5c7e1-3a4f-4b8e-9c10-5e6f7a8b9c0d",
    "nome_file": "esposto_pollaio.pdf",
    "tipo_mime": "application/pdf",
    "sha256": "9f2c…e41a"
  },
  "contesto": {
    "protocollo_noto": "0005120/2025",
    "canale": "caricamento_manuale"
  }
}
```

- `id_lavoro` lo genera l'applicazione: un secondo invio con lo stesso id
  non crea un secondo lavoro (idempotenza).
- Il motore verifica `sha256`; se non coincide risponde `422`
  `impronta_non_coincide`.
- `contesto` è facoltativo e serve solo come aiuto (es. protocollo già
  noto dall'arrivo); il motore restituisce comunque ciò che legge nel
  documento.

Risposta `202`:

```json
{ "id_lavoro": "6f1c2a0e-8b7d-4d5e-9a31-0c2b9e4f7a10", "stato": "in_coda" }
```

### 2.3 `GET /v1/analisi/{id_lavoro}`

Mentre lavora:

```json
{ "id_lavoro": "6f1c…7a10", "stato": "in_corso", "avanzamento": { "pagine_lette": 1, "pagine_totali": 3 } }
```

Concluso: `stato: "completato"` e il campo `risultato` (sezione 3).
In errore: `stato: "errore"` e il campo `errore` (sezione 5).

---

## 3. Risultato

Il risultato descrive **un documento**. Le voci della scheda portano sempre
la **frase del documento** che le giustifica, e la pagina dove si trova.

```json
{
  "versione_contratto": "1.0",
  "versione_motore": "2.3.0",
  "documento": { "id": "d2b5…9c0d", "sha256": "9f2c…e41a" },

  "tipo_documento": {
    "valore": "esposto",
    "motivo": "Il mittente è un privato che descrive un problema e chiede un intervento."
  },

  "protocollo": {
    "numero": "0005120/2025",
    "data": "2025-04-11",
    "frase": "Prot. n. 0005120/2025 del 11/04/2025",
    "pagina": 1
  },

  "pagine": [
    {
      "numero": 1,
      "acquisizione": "testo_nativo",
      "testo": "Prot. n. 0005120/2025 del 11/04/2025\nOggetto: esposto per pollaio…",
      "lettura_incerta": false,
      "motivo_incertezza": null
    },
    {
      "numero": 2,
      "acquisizione": "ocr_manoscritto",
      "testo": "Io sottoscritto … circa 40 galline + 6 oche tenute a meno di 10 metri dalla mia finestra …",
      "lettura_incerta": true,
      "motivo_incertezza": "Foglio scritto a mano: nomi, date e numeri vanno controllati sull'originale."
    }
  ],
  "lettura_incerta": true,

  "scheda": {
    "data_doc":     { "valore": "2025-04-09", "frase": "Castelrovo, 9 aprile 2025", "pagina": 2 },
    "comune":       { "valore": "Castelrovo", "frase": "residente in Castelrovo, via dei Gelsi", "pagina": 2 },
    "ambito": [
      { "valore": "Medicina Veterinaria", "frase": "circa 40 galline + 6 oche", "pagina": 2 },
      { "valore": "Igiene pubblica", "frase": "odore insopportabile soprattutto d'estate", "pagina": 2 }
    ],
    "ambito_altro": null,
    "problematica": [
      { "valore": "Condizioni igieniche carenti", "frase": "escrementi accumulati lungo la rete", "pagina": 2 },
      { "valore": "Odori molesti", "frase": "odore insopportabile soprattutto d'estate", "pagina": 2 }
    ],
    "problematica_altro": null,
    "elementi": [
      { "valore": "Presenza escrementi", "frase": "escrementi accumulati lungo la rete", "pagina": 2 },
      { "valore": "Precedenti segnalazioni", "frase": "ho già avvisato i vigili due volte", "pagina": 2 }
    ],
    "elementi_altro": null
  },

  "proposta": {
    "esito": "Accolto",
    "urgenza": "Bassa",
    "azione": ["Sopralluogo congiunto"],
    "motivo": "Chi segnala, dove e cosa sono indicati: istanza completa. La situazione dura da mesi e i vigili sono già stati avvisati due volte, quindi urgenza ridotta.",
    "domanda_decisiva": "L'esposto indica chi segnala, dove e qual è il problema?",
    "da_verificare_sull_originale": [
      "Numero degli animali (pagina 2, manoscritto)",
      "Data del documento (pagina 2, manoscritto)"
    ]
  },

  "temi": [
    {
      "valore": "Animali da reddito",
      "motivo": "Galline e oche tenute in un cortile privato.",
      "frase": "circa 40 galline + 6 oche",
      "pagina": 2
    }
  ]
}
```

### 3.1 Significato dei campi

| Campo | Obbligatorio | Note |
|---|---|---|
| `tipo_documento.valore` | sì | vocabolario `tipo_documento` |
| `protocollo` | no | `null` se il documento non riporta un protocollo leggibile |
| `pagine[]` | sì | una voce per pagina, in ordine; `testo` può essere vuoto |
| `pagine[].acquisizione` | sì | `testo_nativo` (testo già presente nel file), `ocr` (stampato scansionato), `ocr_manoscritto` (scritto a mano), `nessuna` (pagina non leggibile) |
| `pagine[].lettura_incerta` | sì | `true` se il motore non è sicuro del testo di quella pagina |
| `lettura_incerta` | sì | `true` se almeno una pagina è incerta; produce l'avviso in pratica |
| `scheda.*` | sì (anche vuoti) | voce singola: oggetto o `null`; voce multipla: lista, anche vuota |
| `scheda.*.frase` | sì per ogni voce valorizzata | testo **letterale** del documento; massimo 300 caratteri |
| `scheda.*_altro` | no | testo libero quando il valore non è nel vocabolario |
| `proposta.esito`, `urgenza` | sì | vocabolari `esito`, `urgenza` |
| `proposta.azione` | sì | lista (anche vuota), vocabolario `azione` |
| `proposta.motivo` | sì | perché la proposta, in italiano semplice, mostrato all'operatore |
| `proposta.domanda_decisiva` | sì | la domanda del percorso di valutazione che ha determinato l'esito |
| `proposta.da_verificare_sull_originale` | sì | lista (anche vuota) di cose da controllare sul documento originale |
| `temi[]` | sì | uno o più temi proposti per il fascicolo (vocabolario `tema`); l'operatore li conferma |

Date in formato ISO `AAAA-MM-GG`. Testo in UTF-8.

### 3.2 Dove finisce ogni parte nell'applicazione

| Parte del risultato | Dove viene salvata |
|---|---|
| `pagine[]` (testo estratto) | **accanto al documento**, nell'archivio (SharePoint / cartella locale), come `<id_documento>.testo.json`; nel database solo riferimento e impronta |
| `tipo_documento`, `protocollo`, `lettura_incerta`, `scheda`, `proposta`, `temi` | database (`risultato_motore`) |

La proposta **non diventa mai** da sola la valutazione della pratica: precompila
il modulo, e decide l'operatore.

---

## 4. Vocabolari

I valori sono **codici testuali stabili**. L'applicazione tiene i vocabolari in
tabella; un valore sconosciuto non fa fallire il salvataggio ma viene
segnalato (e mostrato come "valore non riconosciuto").

| Vocabolario | Valori (versione 1.0) |
|---|---|
| `tipo_documento` | `esposto`, `inoltro_per_competenza`, `richiesta_ente`, `riscontro_ats`, `integrazione`, `altro` |
| `esito` | `Accolto`, `Archiviato`, `Da approfondire`, `Invio Modulo`, `Altro` |
| `urgenza` | `Bassa`, `Normale`, `Alta`, `Immediata` |
| `azione` | `Sopralluogo`, `Sopralluogo congiunto`, `Contatto segnalante`, `Richiesta integrazione`, `Trasmissione ad altro ente` |
| `tema` | `Cani`, `Gatti e colonie feline`, `Animali da reddito`, `Avvelenamenti` (l'elenco crescerà) |
| `ambito`, `problematica`, `elementi` | **da fissare**: oggi esempi dai mockup (`Medicina Veterinaria`, `Igiene pubblica`; `Condizioni igieniche carenti`, `Odori molesti`; `Presenza escrementi`, `Precedenti segnalazioni`). Gli elenchi definitivi devono coincidere con le scelte usate nelle valutazioni ATS |

Esito, urgenza, azione, ambito, problematica ed elementi usano **le stesse
etichette** delle colonne della valutazione ATS: così proposta dell'IA e
valutazione dell'operatore si confrontano campo per campo.

---

## 5. Errori

```json
{
  "id_lavoro": "6f1c…7a10",
  "stato": "errore",
  "errore": {
    "codice": "documento_illeggibile",
    "messaggio": "Nessuna pagina contiene testo riconoscibile.",
    "ritentabile": false
  }
}
```

| Codice | Ritentabile | Significato |
|---|---|---|
| `formato_non_supportato` | no | tipo di file non gestito |
| `documento_illeggibile` | no | nessun testo ricavabile |
| `impronta_non_coincide` | sì | il file è arrivato danneggiato |
| `tempo_scaduto` | sì | analisi oltre il tempo massimo del motore |
| `occupato` | sì | (solo come `429`) un altro lavoro è in corso |
| `errore_interno` | sì | qualunque altro errore |

`messaggio` non contiene mai testo del documento. Dopo 3 tentativi falliti
l'applicazione porta la pratica in `DA_SMISTARE` con l'avviso "analisi non
disponibile": il lavoro umano non si blocca.

---

## 6. Esempi sintetici

### 6.1 Esposto digitato, nessuna incertezza (risultato abbreviato)

```json
{
  "versione_contratto": "1.0",
  "versione_motore": "2.3.0",
  "documento": { "id": "a1…", "sha256": "…" },
  "tipo_documento": { "valore": "esposto", "motivo": "Email di un privato che segnala animali in difficoltà." },
  "protocollo": { "numero": "0004512/2025", "data": "2025-04-08", "frase": "Protocollo 0004512/2025", "pagina": 1 },
  "pagine": [
    { "numero": 1, "acquisizione": "testo_nativo", "testo": "Buonasera, in via delle Robinie a Borgoverde ci sono cinque cani in un recinto senza riparo, uno zoppica…", "lettura_incerta": false, "motivo_incertezza": null }
  ],
  "lettura_incerta": false,
  "scheda": {
    "data_doc": { "valore": "2025-04-07", "frase": "inviato il 7 aprile 2025 alle 21:15", "pagina": 1 },
    "comune": { "valore": "Borgoverde", "frase": "in via delle Robinie a Borgoverde", "pagina": 1 },
    "ambito": [ { "valore": "Medicina Veterinaria", "frase": "cinque cani in un recinto", "pagina": 1 } ],
    "ambito_altro": null,
    "problematica": [ { "valore": "Benessere animale", "frase": "senza riparo, uno zoppica", "pagina": 1 } ],
    "problematica_altro": null,
    "elementi": [],
    "elementi_altro": null
  },
  "proposta": {
    "esito": "Accolto",
    "urgenza": "Normale",
    "azione": ["Sopralluogo congiunto"],
    "motivo": "Luogo e problema sono precisi; un animale è ferito, quindi urgenza non bassa.",
    "domanda_decisiva": "Ci sono animali feriti o in pericolo immediato?",
    "da_verificare_sull_originale": []
  },
  "temi": [ { "valore": "Cani", "motivo": "Cani detenuti in un recinto.", "frase": "cinque cani in un recinto", "pagina": 1 } ]
}
```

### 6.2 Foglio scritto a mano, lettura incerta

È l'esempio completo della sezione 3 (pollaio a Castelrovo).

### 6.3 Riscontro ATS (stesso protocollo di un esposto)

```json
{
  "tipo_documento": { "valore": "riscontro_ats", "motivo": "Lettera di ATS al segnalante che riferisce l'esito del sopralluogo." },
  "protocollo": { "numero": "0003177/2025", "data": "2025-04-02", "frase": "Rif. Prot. 0003177/2025", "pagina": 1 },
  "lettura_incerta": false,
  "proposta": {
    "esito": "Accolto",
    "urgenza": "Bassa",
    "azione": [],
    "motivo": "È la risposta di ATS a un esposto già trattato: nessuna nuova azione.",
    "domanda_decisiva": "Il documento è una risposta di ATS a un esposto esistente?",
    "da_verificare_sull_originale": []
  },
  "temi": [ { "valore": "Cani", "motivo": "Riferito a un cane tenuto alla catena.", "frase": "il cane tenuto alla catena", "pagina": 1 } ]
}
```

L'applicazione lo collega automaticamente all'esposto con lo stesso
protocollo; nel percorso della pratica il passo "Riscontro" passa da *atteso*
a *concluso*.

### 6.4 Errore

```json
{ "id_lavoro": "…", "stato": "errore", "errore": { "codice": "formato_non_supportato", "messaggio": "Tipo di file .pages non gestito.", "ritentabile": false } }
```

---

## 7. Regole di evoluzione

- `versione_contratto` segue `MAGGIORE.MINORE`. Aggiungere campi facoltativi
  o valori di vocabolario = versione minore; togliere o rinominare campi =
  versione maggiore, concordata da entrambe le parti.
- L'applicazione ignora i campi che non conosce.
- Ogni modifica a questo documento passa dal ramo `backend` con revisione.
- Il **finto motore** dell'applicazione implementa esattamente questo
  contratto ed è il riferimento per i test di contratto.
