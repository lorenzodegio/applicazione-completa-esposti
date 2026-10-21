"""Un unico filtro decide quali pratiche un utente vede (piano, sezione 6).

Fuori dal perimetro la pratica non esiste: 404, mai 403.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import Select, false, select
from sqlalchemy.orm import Session

from .enums import Ruolo
from .models import Pratica, Utente


def pratiche_visibili(utente: Utente) -> Select[tuple[Pratica]]:
    q = select(Pratica)
    if utente.ruolo == Ruolo.smistatore:
        return q
    if utente.ruolo == Ruolo.operatore:
        # una pratica non smistata ha ufficio_id NULL: NULL = x non è mai vero
        return q.where(Pratica.ufficio_id == utente.ufficio_id)
    return q.where(false())  # l'amministratore non vede le pratiche


def carica_pratica(db: Session, utente: Utente, pratica_id: uuid.UUID, *, per_modifica: bool = False) -> Pratica:
    q = pratiche_visibili(utente).where(Pratica.id == pratica_id)
    if per_modifica:
        q = q.with_for_update(of=Pratica)
    pratica = db.execute(q).scalar_one_or_none()
    if pratica is None:
        raise HTTPException(404, "Pratica non trovata")
    return pratica
