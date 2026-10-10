# backend/api

Server applicativo del backoffice: **FastAPI + PostgreSQL**.

Responsabilità:
- autenticazione (utenti locali con ruolo; predisposto per l'accesso Microsoft di ATS);
- permessi per ruolo (smistatore, operatore, amministratore), applicati **qui**, mai solo nel browser, e coperti da test;
- pratiche, assegnazioni, stati, note interne, collegamenti tra pratiche;
- registro delle azioni (chi, cosa, quando);
- invio dei lavori al motore tramite `backend/motore` e accesso ai documenti tramite `backend/documenti`.

Ancora nessun codice.
