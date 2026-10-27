# Modello di segnalazione (collaudo)

Su GitHub: repository `lorenzodegio/applicazione-completa-esposti` → **Issues** → **New issue** →
**«Problema di collaudo»** (il modulo chiede gli stessi campi qui sotto). Se il modulo non c'è, apri una
issue vuota e copia questo testo.

**Una issue per problema.** Se lo stesso problema compare in più prove, una sola issue con tutti i codici.
**Solo dati sintetici**: niente documenti reali, niente nomi o dati veri, screenshot solo della finestra
dell'applicazione con dati di prova (nient'altro sullo schermo).

---

**Titolo:** `[COLLAUDO] <codice> — <frase breve>` (es. `[COLLAUDO] INB-06 — il secondo salvataggio sovrascrive il primo`)

**Codice della prova:** (es. INB-06; più codici separati da virgola)

**Ambiente**
- Motore: finto / vero
- Browser e versione: (es. Edge 141)
- Dove: workstation ATS / PC personale
- Versione: risultato di `git log --oneline -1` sul ramo `dev`

**Passi** (numerati, esattamente come li hai fatti; utente usato)
1.
2.
3.

**Atteso** (dalla checklist)

**Ottenuto** (cosa è successo davvero; messaggi esatti tra virgolette)

**Si ripete?** sempre / a volte / una volta sola

**Gravità**
- *Bloccante*: impedisce di proseguire o mostra dati a chi non dovrebbe vederli
- *Grave*: risultato sbagliato, ma si può aggirare
- *Lieve*: aspetto, testi, comodità

**Screenshot** (solo dati sintetici) e, se servono, righe di log (`docker compose logs --tail 50 api worker`,
controllando che non contengano dati personali).
