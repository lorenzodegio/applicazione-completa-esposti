> **Nota (riorganizzazione del repository):** il mockup è stato diviso in
> `frontend/frontoffice/` (cittadino, congelato) e `frontend/backoffice/`
> (operatore, riferimento). `styles/`, `assets/` e `js/app.js` sono copiati
> in entrambe le cartelle. I percorsi citati sotto sono quelli originali.

# Sportello Esposti — ATS Insubria

Mockup funzionante di un portale URP generico, costruito prendendo come
modello l'esempio S.I.R.E. (esposti veterinari ATS Insubria) ma pensato fin
dall'inizio per essere esteso a qualsiasi ambito della Pubblica
Amministrazione. Gli esposti veterinari restano solo il primo caso d'uso.

## Struttura del progetto

```
index.html                  → homepage con descrizione del servizio
cittadino.html               → wizard di invio pratica (3 passaggi)
dashboard-operatore.html     → area riservata operatori
styles/main.css              → design system condiviso
js/app.js                    → utility condivise, mock DB, dati demo
js/ai-service.js             → PUNTO UNICO di integrazione con il motore IA
js/citizen-flow.js           → logica del wizard cittadino
js/operator-dashboard.js     → logica del pannello operatore
assets/logo.svg              → logo placeholder
```

Apri semplicemente `index.html` in un browser (idealmente servito da un
piccolo server locale, es. `npx serve` o l'estensione "Live Server", per
evitare limitazioni dei browser sui percorsi `file://`).

## Il flusso IA, oggi (mock) e domani (reale)

1. Il cittadino scrive una descrizione libera al passo 1 del wizard.
2. `citizen-flow.js` chiama `URPAIService.classificaPratica(testo, tipoPratica)`.
3. Il metodo restituisce una `Promise` che risolve con un oggetto strutturato:
   ```json
   {
     "ambito": "Veterinario",
     "messaggio": "Stai effettuando una segnalazione in ambito veterinario?",
     "dati_richiesti": ["Codice fiscale", "Nome e cognome", "Recapito", "Luogo della segnalazione", "Descrizione dettagliata"],
     "ufficio_destinazione": "Dipartimento di Prevenzione Veterinaria",
     "richiede_conferma": true,
     "confidenza": "94%"
   }
   ```
   (`confidenza` è un campo extra rispetto alla specifica originale, comodo
   per la demo ma facoltativo: rimuoverlo non rompe nulla.)
4. Il frontend mostra il messaggio e genera **dinamicamente** un campo per
   ogni voce di `dati_richiesti`, pre-compilando quelli già noti (es. la
   descrizione già scritta al passo 1).
5. Il cittadino conferma o completa i dati richiesti, poi vede un riepilogo
   finale prima dell'invio.

Per collegare il vero motore IA basta riscrivere il corpo di
`URPAIService.classificaPratica` in `js/ai-service.js` con una vera chiamata,
ad esempio:

```javascript
static classificaPratica(testo, tipoPratica) {
    return fetch('/api/ai/classifica', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ testo, tipoPratica })
    }).then(res => res.json());
}
```

**Nessun'altra parte del frontend deve cambiare**, a patto che la risposta
mantenga la stessa forma. Tutto il resto del codice (rendering dei campi,
riepilogo, salvataggio) lavora già in modo generico sulla struttura della
risposta, non sui valori specifici del dominio veterinario.

## Perché il sistema è già pensato per altri ambiti

- **Gli "ambiti" non sono un enum fisso.** Qualunque stringa restituita
  dall'IA viene colorata automaticamente con una palette basata su hash
  (`getColorForAmbito` in `app.js`): un ambito mai visto prima viene
  visualizzato correttamente senza toccare il codice.
- **I "dati_richiesti" non sono hardcoded.** Il form del passo 2 viene
  generato in un ciclo a partire dall'array restituito dall'IA
  (`renderDynamicFields` in `citizen-flow.js`). Non esiste da nessuna parte
  un controllo tipo `if (categoria === 'maltrattamento')`.
- **L'ufficio suggerito dall'IA viene aggiunto automaticamente** alla lista
  degli uffici selezionabili nel pannello operatore, anche se non è tra
  quelli predefiniti in `UFFICI_OPERATORI_BASE` (vedi `openDettaglio` in
  `operator-dashboard.js`).
- Il motore mock in `ai-service.js` sa già classificare più ambiti
  (Veterinario, Ambiente, Edilizia, Tributi, Accesso agli Atti, più un
  fallback "Da Classificare") solo per rendere credibile la demo: quando
  arriverà il modello vero, quella logica va sostituita, ma il resto
  dell'app non se ne accorge.

## Stati di una pratica

`RICEVUTA` → `DA_VALUTARE` → `ASSEGNATA` → `IN_LAVORAZIONE` → `CHIUSA`

Non ci sono ancora regole di transizione: l'operatore può impostare
liberamente qualunque stato, come richiesto per questa prima versione. Lo
stesso vale per assegnazione e note interne.

## Dati demo

Al primo avvio, se il "database" (`localStorage`) è vuoto, vengono create 6
pratiche di esempio distribuite su ambiti e stati diversi, per mostrare da
subito il pannello operatore popolato (`seedDemoData` in `app.js`). Per
ripartire da zero basta svuotare il localStorage del browser (chiave
`urp_pratiche_db`).

## Limiti di questo mockup

- Nessun backend reale: tutto è salvato nel `localStorage` del browser
  (dati locali al singolo browser, non condivisi tra utenti/dispositivi).
- Gli allegati non vengono realmente caricati: viene salvato solo nome,
  dimensione e tipo del file scelto, non il contenuto.
- Nessuna autenticazione reale: l'accesso SPID/CIE e l'identità
  dell'operatore sono simulati.
- Nessun workflow complesso sugli stati/assegnazioni, come da indicazioni
  per questa prima versione.
