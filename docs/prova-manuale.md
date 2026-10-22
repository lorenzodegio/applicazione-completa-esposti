# Prova manuale: credenziali, indirizzi e percorso di prova

Questa guida serve per provare l'applicazione nel browser con i **dati demo**. Tutto ciò che
trovi qui è **sintetico** e vale **solo in sviluppo**: mai usare queste credenziali o questi dati
con informazioni reali, e mai metterli in un ambiente diverso dal PC di sviluppo.

## 1. Accessi all'applicazione (browser)

Indirizzo: **http://localhost:5173**. La password è la stessa per tutti: **`password-sintetica-1`**.

| Utente | Ruolo e ufficio | Cosa vede | Per cosa serve provarlo |
|---|---|---|---|
| `op.vet` | Operatore, **Medicina Veterinaria** | Solo le pratiche del suo ufficio. Menu: Home, Inbox, Fascicoli, Gestione pratiche | È l'utente principale: validare esposti, correggere la proposta dell'IA, aggiungere azioni e note |
| `op.igp` | Operatore, **Igiene pubblica** | Solo le pratiche del suo ufficio | Verificare i **permessi**: non deve vedere le pratiche di Veterinaria |
| `smistatore` | Smistatore | **Tutte** le pratiche. Menu: come l'operatore, in più **Smistamento** | Assegnare le pratiche agli uffici, riassegnarle, caricare nuovi esposti, riaprire pratiche chiuse |
| `admin` | Amministratore | **Solo** Uffici e Utenti, nessuna pratica | Creare uffici e utenti, disattivarli, reimpostare password |

Se sbagli la password **5 volte** con lo stesso nome utente, l'accesso resta bloccato per circa
**15 minuti** (messaggio "Troppi tentativi").

## 2. Credenziali del database

Non si usano nel browser: le usano l'API, il worker, le migrazioni e la demo.

| Cosa | Valore | A cosa serve |
|---|---|---|
| Server | `localhost`, porta `5432` | Il Postgres installato sul tuo PC |
| Utente dell'applicazione | `esposti` | Con questo l'applicazione si collega al database |
| Password dell'applicazione | `esposti` | |
| Database | `esposti` | Contiene utenti, pratiche, registro delle azioni |
| Superutente di Postgres | `postgres` + **la password scelta quando hai installato Postgres** | **Non è nel progetto.** Serve solo a `crea-database.bat`, una volta, per creare utente e database `esposti` |

Questi valori sono quelli predefiniti in `backend\api\api\config.py`. Per usare un database diverso
crea il file `backend\api\.env` (è già escluso da git) con una riga:

```
ESPOSTI_DATABASE_URL=postgresql+psycopg://UTENTE:PASSWORD@localhost:5432/NOMEDATABASE
```

Usa sempre un database **nuovo e dedicato**, mai uno con dati reali.

## 3. Indirizzi

| Indirizzo | Cos'è |
|---|---|
| http://localhost:5173 | L'interfaccia (frontend) |
| http://localhost:8000 | Il server API |
| http://localhost:8000/docs | Documentazione interattiva dell'API (per provare le chiamate: prima `POST /api/v1/auth/login`) |

## 4. Come si avvia (Windows)

Tutti i file sono nella cartella `scripts\`, si lanciano con doppio clic. Le tre finestre devono
restare aperte mentre provi.

| Ordine | File | Cosa fa |
|---|---|---|
| (prima volta) | `controlla-requisiti.bat` | Controlla Python, Node, Postgres, porte e file; non modifica nulla |
| (prima volta) | `crea-database.bat` | Crea utente e database `esposti` (chiede la password di `postgres`) |
| 1 | `avvia-1-api.bat` | Prepara Python, migra il database, crea i dati demo, avvia le API |
| 2 | `avvia-2-worker.bat` | Fa girare il **finto motore**: senza, i documenti caricati restano "in analisi" |
| 3 | `avvia-3-frontend.bat` | Avvia l'interfaccia |
| (se serve) | `ripara-accessi.bat` | Controlla gli utenti demo e li ricrea o ripara se il login non funziona |

## 5. Dove sono scritte queste credenziali nel progetto

| File | Cosa contiene |
|---|---|
| `backend\api\api\seed.py` | La fonte: i 4 utenti demo e la password |
| `backend\api\api\config.py` | I valori predefiniti del database |
| `frontend\backoffice\README.md` | La riga "Accessi demo" |
| `scripts\avvia-3-frontend.bat` | Le mostra all'avvio e nel titolo della finestra |
| `frontend\backoffice\src\test\live.test.tsx` | La password, usata dai test end-to-end |

Per cambiare la password demo imposta `ESPOSTI_SEED_PASSWORD` (per esempio in `backend\api\.env`)
**prima** di creare la demo. Se la demo esiste già, usa `ripara-accessi.bat` dopo aver cambiato il valore.

## 6. Dati demo: cosa trovi

Creati da `python -m api.seed` (pratiche di base, **senza** proposta dell'IA) e `python -m api.demo`
(pratiche con titolo che finisce per `_demo`, **analizzate dal finto motore**).

| Pratica | Stato iniziale | Ufficio | Cosa ti permette di provare |
|---|---|---|---|
| Esposto cani via robinie_demo | Da validare | Veterinaria | Il caso "pulito": proposta dell'IA, tema Cani |
| Foglio manoscritto pollaio_demo | Da validare | Veterinaria | **Lettura incerta**: avviso e "da verificare sull'originale" |
| Esposto gatti via molino_demo | Da validare | Veterinaria | Un altro esposto con proposta |
| Esposto instabile esche_demo | Da validare | Veterinaria | Il motore ha fallito la prima volta e riuscito alla seconda |
| Riscontro ats cane catena_demo | Da validare | Veterinaria | Un documento riconosciuto come **riscontro ATS** |
| Esposto rumori laboratorio_demo | Da validare | Igiene pubblica | Permessi: la vede solo `op.igp` (e lo smistatore) |
| Esposto cane libero_demo | Da smistare | nessuno | Da assegnare con lo smistatore |
| Lettera ente_demo | Da smistare | nessuno | **Analisi non disponibile** (formato non gestito): si tratta a mano |
| Odori da allevamento, Colonia felina in cortile | Da validare | Veterinaria | Pratiche **senza** proposta dell'IA |
| Rumori notturni da laboratorio | Da validare | Igiene pubblica | Come sopra |
| Gatti in un'abitazione | In lavorazione | Veterinaria | Collegamenti e percorso con riscontro (vedi sotto) |
| Cane alla catena (riscontro) | Chiusa | Veterinaria | Pratica chiusa |
| Pollaio a ridosso del confine, Cinque cani in un recinto senza riparo | Da smistare | nessuno | Da assegnare |
| Documento in analisi | In analisi | nessuno | Stato iniziale del motore |

**Il nome del file caricato sceglie lo scenario del finto motore.** Quando carichi un esposto nuovo
(Smistamento → "Carica un nuovo esposto") dai al file uno di questi nomi:

| Il nome contiene | Risultato |
|---|---|
| (qualsiasi altro nome) | Esposto digitato, nessuna incertezza |
| `manoscritto` o `incerto` | Lettura incerta (foglio scritto a mano) |
| `riscontro` | Riscontro ATS |
| `errore`, oppure estensione `.pages` | Errore "formato non gestito": non si ritenta |
| `illeggibile` | Documento illeggibile: non si ritenta |
| `scaduto` | Errore di tempo: 3 tentativi, poi analisi non disponibile |
| `instabile` | Fallisce la prima volta, riesce alla seconda |
| `invalido` | Risultato fuori contratto: viene scartato |

Il finto motore restituisce sempre gli stessi esempi, quindi molte pratiche demo condividono il
**protocollo inventato `0004512/2025`**: compariranno tutte collegate fra loro come "Stesso
protocollo". È normale, non un errore.

## 7. Percorso di prova (circa 15 minuti)

1. **`op.vet` → Home.** All'inizio: *Da validare 7*, *In lavorazione 1*, *Lettura incerta 1*, *Senza riscontro 0*.
2. **Inbox → "Foglio manoscritto pollaio_demo".** Compare l'avviso di lettura incerta; a destra la
   proposta dell'IA, a sinistra la tua valutazione già compilata. "Apri il PDF e lo storico" porta alla scheda.
3. **Valida "Esposto cani via robinie_demo"** cambiando l'urgenza in *Alta* → "Conferma e vai al
   prossimo". In **Gestione pratiche** cerca "robinie": stato *In lavorazione*, fascicolo *Cani*, e sotto
   l'esito la nota "IA: urgenza Normale, operatore: Alta" (il **disaccordo**). La Home lo segnala.
4. **Fascicoli** (prima erano vuoti, perché nessun tema era confermato): ora *Cani* contiene la pratica,
   con il suo percorso a destra.
5. **Restituisci "Colonia felina in cortile"** (pulsante in Inbox) scrivendo un motivo: sparisce dalla tua Inbox.
6. **`smistatore` → Smistamento.** Ora vedi la pratica restituita fra quelle da assegnare (insieme a
   "Lettera ente_demo", "Esposto cane libero_demo" e le due pratiche di base). Assegna "Esposto cane libero_demo"
   a **Igiene pubblica**, poi accedi come `op.igp`: la trovi nella sua Inbox.
7. **Carica un nuovo esposto** (Smistamento, con il worker acceso) con un file chiamato per esempio
   `foglio_manoscritto_prova.pdf`: nella scheda vedi lo stato dell'analisi passare da "in corso" a "analizzato".
8. **Permessi.** Con `op.igp` la lista contiene solo le pratiche di Igiene pubblica. Incollando
   nell'indirizzo l'id di una pratica di Veterinaria compare "Non trovato" (non "vietato").
9. **Collegamenti e percorso.** Con `op.vet` apri "Gatti in un'abitazione": nella scheda *Collegamenti*
   due pratiche "Stesso protocollo" (`0003177/2025`), nella scheda *Percorso* il passo "Riscontro ricevuto".
10. **`admin`.** Crea un utente (operatore, ufficio Veterinaria), poi disattivalo: se era connesso, la sua sessione cade.
11. **Scheda "Note e registro"** di una pratica che hai modificato: ogni azione compare nel registro,
    senza i testi liberi.

## 8. Se qualcosa non va

| Sintomo | Cosa fare |
|---|---|
| "Credenziali non valide" | Lancia `ripara-accessi.bat`; riscrivi la password a mano (il browser potrebbe averne compilata un'altra) |
| "Troppi tentativi" | Aspetta circa 15 minuti |
| `avvia-1-api.bat`: "autenticazione con password fallita" | Lancia `crea-database.bat` e poi rilancia il file 1 |
| `avvia-1-api.bat`: connessione rifiutata | Postgres non è acceso (o Docker, se lo usi) |
| Un documento resta "in analisi" | Il worker (file 2) non è acceso |
| L'interfaccia non si collega alle API | Controlla che il file 1 sia ancora aperto e mostri "Application startup complete" |
| Porta 8000 o 5173 occupata | Chiudi la finestra della prova precedente |
| Vuoi ripartire da zero | Ricrea il database `esposti` e rilancia il file 1 (la demo si rifà) |
