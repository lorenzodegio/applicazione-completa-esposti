import datetime as dt

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .enums import Ruolo
from .models import Sessione, Utente
from .security import hash_token

COOKIE_SESSIONE = "esposti_sessione"


def utente_corrente(
    token: str | None = Cookie(default=None, alias=COOKIE_SESSIONE),
    db: Session = Depends(get_db),
) -> Utente:
    if not token:
        raise HTTPException(401, "Accesso richiesto")
    sessione = db.get(Sessione, hash_token(token))
    ora = dt.datetime.now(dt.timezone.utc)
    if sessione is None or sessione.revocata or sessione.scade_il <= ora:
        raise HTTPException(401, "Sessione non valida o scaduta")
    utente = db.get(Utente, sessione.utente_id)
    if utente is None or not utente.attivo:
        raise HTTPException(401, "Sessione non valida o scaduta")
    return utente


def richiedi_ruoli(*ruoli: Ruolo):
    def dipendenza(utente: Utente = Depends(utente_corrente)) -> Utente:
        if utente.ruolo not in ruoli:
            raise HTTPException(403, "Operazione non consentita al tuo ruolo")
        return utente
    return dipendenza


solo_smistatore = richiedi_ruoli(Ruolo.smistatore)
solo_operatore = richiedi_ruoli(Ruolo.operatore)
solo_amministratore = richiedi_ruoli(Ruolo.amministratore)
smistatore_o_operatore = richiedi_ruoli(Ruolo.smistatore, Ruolo.operatore)
