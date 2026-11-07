# Esiti del collaudo — Khalil

- **Tester:** Khalil
- **Date del collaudo:** dal 07 al 08
- **Versione provata:** `git log --oneline -1` sul ramo `dev` → a61871f (HEAD -> dev, origin/dev) Unione di frontend in dev
- **Dove:** workstation ATS
- **Browser:** Chrome, Edge
- **Motore vero provato?** sì

## Conteggi per area

Solo le aree che ti erano assegnate (sezione 6 della checklist) più quelle in comune.

| Area | Prove | OK | KO | N/A |
|---|---|---|---|---|
| 1. Accesso | 7 | | | |
| 2. Permessi e sicurezza | 13 | 13 | 0 | 0 |
| 3. Caricamento | 12 | 12 | 0 | 0 |
| 4. Motore | 16 | 16 | 0 | 0 |
| 5. Smistamento | 8 | | | |
| 6. Inbox e valutazione | 10 | | | |
| 7. Pratica e storico | 11 | | | |
| 8. Fascicoli e temi | 7 | | | |
| 9. Gestione pratiche e Home | 8 | | | |
| 10. Registro delle azioni | 5 | 5 | 0 | 0 |
| 11. Amministrazione | 8 | 7 | 1 | 0 |
| 12. Robustezza | 7 | 7 | 0 | 0 |
| 13. Privacy | 5 | 5 | 0 | 0 |
| **Totale** | 66 | 65 | 1 | 0 |

## Problemi trovati (KO)

| Codice | Issue | Gravità | In breve |
|---|---|---|---|
| AMM-07 | #1 | Bloccante | Non è presente una sezione/bottone per permettere all'admin di assegnare un ufficio differente |

## Prove non applicabili (N/A) e perché

| Codice | Motivo |
|---|---|
| | |

## Tempi del motore vero (se provato)

| Documento | Secondi |
|---|---|
| digitale      | 36s |
| word          | 20s |
| manoscritto 1 | 45s |
| manoscritto 2 | 51s |
| manoscritto 3 | 51s |
| scansione     | 1m 18s |


## Impressioni generali

- Dopo aver caricato un documento, Il messaggio di errore si sovrappone alla dimensione del file e si nota.
- E' un po' brutto dover scorrere all'infinito con la rotella del mouse per scorrere la lista di esposti,
si potrebbero diminuire il numero di esposti prima della visualizzazione dei bottoni "prossima pagina" oppure una banda di scorrimento laterale.
Questo anche di dover scorrere all'infinito per cambiare utente a fine pagina.
- Diminuire la dimensione dei "box" che contengono gli elementi per aggiungere un allegato,
questo perché altrimenti se clicco sulla destra della pagina mi prende l'input e mi apre la finestra, finendo di aggiungere un documento per sbaglio.

Per il resto molto intuitiva e semplice.
