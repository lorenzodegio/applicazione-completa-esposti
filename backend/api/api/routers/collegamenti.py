import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..collegamenti import collegamenti_visti, id_visibili
from ..db import get_db
from ..deps import smistatore_o_operatore
from ..models import Collegamento, Pratica, TipoCollegamento, Utente
from ..percorso import percorso
from ..permessi import carica_pratica, pratiche_visibili
from ..registro import registra
from ..schemas import (
    CollegamentoIn, CollegamentoOut, PassoPercorso, RicercaRapidaOut,
)
import datetime as dt

router = APIRouter(tags=["collegamenti"])


def _escape(t: str) -> str:
    return t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Va registrato PRIMA di /pratiche/{id}: "ricerca-rapida" non è un uuid.
@router.get("/pratiche/ricerca-rapida", response_model=list[RicercaRapidaOut])
def ricerca_rapida(q: str = Query(min_length=2, max_length=100), escludi: uuid.UUID | None = None,
                   utente: Utente = Depends(smistatore_o_operatore), db: Session = Depends(get_db)) -> list[Pratica]:
    """Per scegliere la pratica da collegare: solo quelle che l'utente vede."""
    t = f"%{_escape(q)}%"
    stmt = pratiche_visibili(utente).where(or_(Pratica.numero.ilike(t), Pratica.protocollo.ilike(t),
                                              Pratica.titolo.ilike(t), Pratica.comune.ilike(t)))
    if escludi:
        stmt = stmt.where(Pratica.id != escludi)
    return list(db.execute(stmt.order_by(Pratica.creata_il.desc(), Pratica.id).limit(10)).scalars())


@router.get("/pratiche/{pratica_id}/collegamenti", response_model=list[CollegamentoOut])
def elenco(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
           db: Session = Depends(get_db)) -> list[CollegamentoOut]:
    return collegamenti_visti(db, utente, carica_pratica(db, utente, pratica_id))


@router.post("/pratiche/{pratica_id}/collegamenti", response_model=CollegamentoOut, status_code=201)
def crea(pratica_id: uuid.UUID, dati: CollegamentoIn, utente: Utente = Depends(smistatore_o_operatore),
         db: Session = Depends(get_db)) -> CollegamentoOut:
    """Tra pratiche che l'utente vede entrambe; l'altra, se non la vede, «non esiste» (404)."""
    da = carica_pratica(db, utente, pratica_id)
    a = carica_pratica(db, utente, dati.pratica_id)
    if da.id == a.id:
        raise HTTPException(422, "Una pratica non si collega a sé stessa")
    tipo = db.get(TipoCollegamento, dati.tipo_id)
    if tipo is None or not tipo.manuale:
        raise HTTPException(422, "Tipo di collegamento non valido")
    verso = [(da.id, a.id)] if tipo.etichetta_inversa else [(da.id, a.id), (a.id, da.id)]  # simmetrico: due versi
    doppio = db.execute(select(Collegamento.id).where(
        Collegamento.rimosso_il.is_(None), Collegamento.tipo_id == tipo.id,
        or_(*[(Collegamento.pratica_da_id == x) & (Collegamento.pratica_a_id == y) for x, y in verso])).limit(1)).first()
    if doppio:
        raise HTTPException(409, "Questo collegamento esiste già")
    c = Collegamento(pratica_da_id=da.id, pratica_a_id=a.id, tipo_id=tipo.id, nota=dati.nota, creato_da=utente.id)
    db.add(c)
    db.flush()
    for p in (da, a):
        registra(db, utente_id=utente.id, azione="collegamento.crea", oggetto_tipo="collegamento", oggetto_id=c.id,
                 pratica_id=p.id, dettagli={"tipo": tipo.codice, "da": str(da.id), "a": str(a.id)})
    db.commit()
    return next(x for x in collegamenti_visti(db, utente, da) if x.id == c.id)


@router.delete("/collegamenti/{collegamento_id}", status_code=204)
def rimuovi(collegamento_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
            db: Session = Depends(get_db)) -> None:
    """Rimozione logica. Basta vedere uno dei due lati; altrimenti il collegamento «non esiste»."""
    c = db.get(Collegamento, collegamento_id)
    if c is None or c.rimosso_il is not None or not id_visibili(db, utente, [c.pratica_da_id, c.pratica_a_id]):
        raise HTTPException(404, "Collegamento non trovato")
    c.rimosso_da, c.rimosso_il = utente.id, dt.datetime.now(dt.timezone.utc)
    for pid in (c.pratica_da_id, c.pratica_a_id):
        registra(db, utente_id=utente.id, azione="collegamento.rimuovi", oggetto_tipo="collegamento",
                 oggetto_id=c.id, pratica_id=pid, dettagli={"tipo": c.tipo.codice})
    db.commit()


@router.get("/pratiche/{pratica_id}/percorso", response_model=list[PassoPercorso])
def percorso_pratica(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                     db: Session = Depends(get_db)) -> list[PassoPercorso]:
    return percorso(db, utente, carica_pratica(db, utente, pratica_id))
