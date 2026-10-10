# backend/motore

**Solo il connettore** verso il motore di classificazione. Il motore vero
vive fuori da questo repository e qui non va copiato, letto o montato.

- Il motore gira come servizio Docker separato.
- Le richieste passano da una coda di lavori, elaborati uno alla volta.
- All'inizio si usa un **finto motore** che restituisce dati con la stessa
  forma di quelli reali (proposta, motivo, avviso di lettura incerta, testo
  estratto, scheda precompilata).
- La proposta dell'IA è un suggerimento: decide sempre la persona.

Ancora nessun codice.
