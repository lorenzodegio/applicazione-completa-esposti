"""Collegamenti tra pratiche: automatici (stesso protocollo, calcolati a ogni lettura) e manuali.

Una pratica fuori dal perimetro dell'utente si mostra solo con numero, ufficio e stato, senza `id`:
non c'è nulla da aprire. L'id compare solo per ciò che l'utente può già vedere.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .models import Collegamento, Pratica, TipoCollegamento, Utente
from .permessi import pratiche_visibili
from .schemas import CollegamentoOut, PraticaRef, TipoCollegamentoOut


@dataclass
class Collegata:
    pratica: Pratica
    tipo: TipoCollegamento
    etichetta: str
    collegamento: Collegamento | None  # None = automatico


def collegate(db: Session, pratica: Pratica) -> list[Collegata]:
    """Tutte le pratiche collegate, senza guardare i permessi (lo si fa in uscita)."""
    out: list[Collegata] = []
    if pratica.chiave_protocollo:  # numero e anno: un protocollo senza anno non collega nulla
        tipo = db.execute(select(TipoCollegamento).where(TipoCollegamento.codice == "STESSO_PROTOCOLLO")).scalar_one()
        for altra in db.execute(select(Pratica).where(Pratica.chiave_protocollo == pratica.chiave_protocollo,
                                                       Pratica.id != pratica.id)
                                .order_by(Pratica.creata_il, Pratica.id)).scalars():
            out.append(Collegata(altra, tipo, tipo.etichetta, None))
    manuali = db.execute(select(Collegamento).where(
        Collegamento.rimosso_il.is_(None),
        or_(Collegamento.pratica_da_id == pratica.id, Collegamento.pratica_a_id == pratica.id))
        .order_by(Collegamento.creato_il, Collegamento.id)).scalars().all()
    for c in manuali:
        in_uscita = c.pratica_da_id == pratica.id
        altra = db.get(Pratica, c.pratica_a_id if in_uscita else c.pratica_da_id)
        etichetta = c.tipo.etichetta if in_uscita else (c.tipo.etichetta_inversa or c.tipo.etichetta)
        out.append(Collegata(altra, c.tipo, etichetta, c))
    return out


def riferimento(p: Pratica, visibile: bool) -> PraticaRef:
    base = dict(numero=p.numero, ufficio=p.ufficio, stato=p.stato)
    if not visibile:
        return PraticaRef(id=None, **base)
    return PraticaRef(id=p.id, tipo=p.tipo, titolo=p.titolo, protocollo=p.protocollo, comune=p.comune, **base)


def id_visibili(db: Session, utente: Utente, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not ids:
        return set()
    return set(db.execute(pratiche_visibili(utente).with_only_columns(Pratica.id).where(Pratica.id.in_(ids))).scalars())


def collegamenti_visti(db: Session, utente: Utente, pratica: Pratica) -> list[CollegamentoOut]:
    righe = collegate(db, pratica)
    visibili = id_visibili(db, utente, [r.pratica.id for r in righe])
    return [CollegamentoOut(
        id=r.collegamento.id if r.collegamento else None, automatico=r.collegamento is None,
        tipo=TipoCollegamentoOut.model_validate(r.tipo), etichetta=r.etichetta,
        nota=r.collegamento.nota if r.collegamento else None,
        pratica=riferimento(r.pratica, r.pratica.id in visibili),
        creato_il=r.collegamento.creato_il if r.collegamento else None) for r in righe]
