# backend/motore

**Solo il connettore** verso il motore di classificazione. Il motore vero
(`classificatore-esposti-v2`) vive fuori da questo repository e qui non va
copiato, letto o montato.

L'interfaccia è definita in [docs/contratto_motore.md](../../docs/contratto_motore.md).

- Il motore gira come servizio Docker separato, raggiunto con `MOTORE_URL`.
- La coda dei lavori è nel database dell'applicazione; un worker elabora
  **un documento alla volta**: scarico temporaneo dall'archivio, invio al
  motore, salvataggio del risultato, cancellazione del temporaneo.
- Un **finto motore** implementa lo stesso contratto con risposte
  sintetiche, per sviluppo e test.
- La proposta dell'IA è un suggerimento: decide sempre la persona.

Struttura prevista: `contratto/` (schema e file di prova), `finto/` (finto
motore), connettore e worker. Ancora nessun codice.
