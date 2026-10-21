import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import solo_amministratore, utente_corrente
from ..enums import Provider, Ruolo
from ..models import Sessione, Ufficio, Utente
from ..registro import registra
from ..schemas import (
    PasswordIn, UfficioIn, UfficioOut, UfficioPatch, UtenteIn, UtenteOut, UtentePatch,
)
from ..security import hash_password

router = APIRouter(tags=["amministrazione"])


# --- Uffici: lettura per tutti, scrittura per l'amministratore ----------------------

@router.get("/uffici", response_model=list[UfficioOut])
def elenco_uffici(_: Utente = Depends(utente_corrente), db: Session = Depends(get_db)) -> list[Ufficio]:
    return list(db.execute(select(Ufficio).order_by(Ufficio.nome)).scalars())


@router.post("/uffici", response_model=UfficioOut, status_code=201)
def crea_ufficio(dati: UfficioIn, admin: Utente = Depends(solo_amministratore),
                 db: Session = Depends(get_db)) -> Ufficio:
    ufficio = Ufficio(codice=dati.codice, nome=dati.nome)
    db.add(ufficio)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Esiste già un ufficio con questo codice")
    registra(db, utente_id=admin.id, azione="ufficio.crea", oggetto_tipo="ufficio", oggetto_id=ufficio.id,
             dettagli={"codice": ufficio.codice})
    db.commit()
    return ufficio


@router.patch("/uffici/{ufficio_id}", response_model=UfficioOut)
def modifica_ufficio(ufficio_id: uuid.UUID, dati: UfficioPatch, admin: Utente = Depends(solo_amministratore),
                     db: Session = Depends(get_db)) -> Ufficio:
    ufficio = db.get(Ufficio, ufficio_id)
    if ufficio is None:
        raise HTTPException(404, "Ufficio non trovato")
    modifiche = dati.model_dump(exclude_unset=True, exclude_none=True)
    for campo, valore in modifiche.items():
        setattr(ufficio, campo, valore)  # gli uffici si disattivano, non si cancellano
    registra(db, utente_id=admin.id, azione="ufficio.modifica", oggetto_tipo="ufficio", oggetto_id=ufficio.id,
             dettagli={"campi": sorted(modifiche)})
    db.commit()
    return ufficio


# --- Utenti ----------------------------------------------------------------------

def _valida_ruolo_ufficio(db: Session, ruolo: Ruolo, ufficio_id: uuid.UUID | None) -> None:
    if ruolo == Ruolo.operatore:
        ufficio = db.get(Ufficio, ufficio_id) if ufficio_id else None
        if ufficio is None or not ufficio.attivo:
            raise HTTPException(422, "Un operatore richiede un ufficio attivo")
    elif ufficio_id is not None:
        raise HTTPException(422, "Solo gli operatori hanno un ufficio")


@router.get("/utenti", response_model=list[UtenteOut])
def elenco_utenti(_: Utente = Depends(solo_amministratore), db: Session = Depends(get_db)) -> list[Utente]:
    return list(db.execute(select(Utente).order_by(Utente.username)).scalars())


@router.post("/utenti", response_model=UtenteOut, status_code=201)
def crea_utente(dati: UtenteIn, admin: Utente = Depends(solo_amministratore),
                db: Session = Depends(get_db)) -> Utente:
    _valida_ruolo_ufficio(db, dati.ruolo, dati.ufficio_id)
    utente = Utente(username=dati.username, nome_visualizzato=dati.nome_visualizzato, email=dati.email,
                    ruolo=dati.ruolo, ufficio_id=dati.ufficio_id, provider=Provider.locale,
                    password_hash=hash_password(dati.password))
    db.add(utente)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Esiste già un utente con questo nome")
    registra(db, utente_id=admin.id, azione="utente.crea", oggetto_tipo="utente", oggetto_id=utente.id,
             dettagli={"ruolo": dati.ruolo.value})
    db.commit()
    return utente


@router.patch("/utenti/{utente_id}", response_model=UtenteOut)
def modifica_utente(utente_id: uuid.UUID, dati: UtentePatch, admin: Utente = Depends(solo_amministratore),
                    db: Session = Depends(get_db)) -> Utente:
    utente = db.get(Utente, utente_id)
    if utente is None:
        raise HTTPException(404, "Utente non trovato")
    campi = dati.model_fields_set
    if utente.id == admin.id and (dati.attivo is False or ("ruolo" in campi and dati.ruolo != admin.ruolo)):
        raise HTTPException(422, "Non puoi disattivare te stesso né cambiare il tuo ruolo")
    ruolo = dati.ruolo if "ruolo" in campi and dati.ruolo else utente.ruolo
    ufficio_id = dati.ufficio_id if "ufficio_id" in campi else utente.ufficio_id
    if ruolo != Ruolo.operatore and "ruolo" in campi and "ufficio_id" not in campi:
        ufficio_id = None  # cambiando ruolo da operatore l'ufficio decade
    _valida_ruolo_ufficio(db, ruolo, ufficio_id)
    modificati = []
    for campo in ("nome_visualizzato", "email", "attivo"):
        if campo in campi and getattr(dati, campo) is not None:
            setattr(utente, campo, getattr(dati, campo))
            modificati.append(campo)
    if ruolo != utente.ruolo or ufficio_id != utente.ufficio_id:
        utente.ruolo, utente.ufficio_id = ruolo, ufficio_id
        modificati += ["ruolo", "ufficio_id"]
    if dati.attivo is False or ruolo != Ruolo.operatore or "ruolo" in modificati:
        for s in db.execute(select(Sessione).where(Sessione.utente_id == utente.id,
                                                   Sessione.revocata.is_(False))).scalars():
            s.revocata = True  # ruolo/ufficio cambiati o utente disattivato: si riaccede
    registra(db, utente_id=admin.id, azione="utente.modifica", oggetto_tipo="utente", oggetto_id=utente.id,
             dettagli={"campi": sorted(set(modificati))})
    db.commit()
    return utente


@router.post("/utenti/{utente_id}/password", status_code=204)
def reimposta_password(utente_id: uuid.UUID, dati: PasswordIn, admin: Utente = Depends(solo_amministratore),
                       db: Session = Depends(get_db)) -> None:
    utente = db.get(Utente, utente_id)
    if utente is None:
        raise HTTPException(404, "Utente non trovato")
    utente.password_hash = hash_password(dati.password)
    for s in db.execute(select(Sessione).where(Sessione.utente_id == utente.id,
                                               Sessione.revocata.is_(False))).scalars():
        s.revocata = True
    registra(db, utente_id=admin.id, azione="utente.password", oggetto_tipo="utente", oggetto_id=utente.id)
    db.commit()
