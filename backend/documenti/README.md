# backend/documenti

Interfaccia unica per leggere e scrivere i documenti delle pratiche
(vedi [piano, sezione 4](../../docs/piano.md#4-documenti-e-archivio)).

- **SharePoint è l'archivio di riferimento**; la macchina elabora soltanto
  (scarico temporaneo, elaborazione, salvataggio, cancellazione).
- Ogni documento ha identificativo d'archivio (SharePoint) e impronta `sha256`.
- Il testo estratto si salva **accanto** al documento, non nel database.
- Implementazioni: **cartella locale** (sviluppo e prima fase, percorso da
  configurazione fuori dal repository) e **SharePoint** (struttura ancora da
  definire).
- Migrazione locale → SharePoint con verifica delle impronte prima di ogni
  cancellazione.
- Il resto del backend usa solo l'interfaccia, mai l'implementazione concreta.

Ancora nessun codice.
