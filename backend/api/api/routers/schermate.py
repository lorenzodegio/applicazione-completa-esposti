"""Home, Fascicoli e configurazione in sola lettura."""
import datetime as dt  # noqa: F401
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from ..arricchimento import arricchisci
from ..db import get_db
from ..deps import smistatore_o_operatore, utente_corrente
from ..enums import Ruolo, Stato, StatoTema
from ..models import (
    Collegamento, Pratica, PraticaTema, Tema, TipoCollegamento, Utente, VoceVocabolario,
    vista_analisi_principale, vista_disaccordo,
)
from ..permessi import pratiche_visibili
from ..schemas import DisaccordoHome, FascicoloOut, HomeOut, Pagina, TemaCatalogoOut, TipoCollegamentoOut

router = APIRouter(tags=["schermate"])

STATI_APERTI = (Stato.DA_SMISTARE, Stato.DA_VALIDARE, Stato.IN_LAVORAZIONE)


def _conteggi_fascicoli(db: Session, utente: Utente, limite: int | None = None) -> list[FascicoloOut]:
    vis = pratiche_visibili(utente).with_only_columns(Pratica.id).subquery()
    n = func.count(func.distinct(PraticaTema.pratica_id))
    stmt = (select(Tema.codice, Tema.nome, n).select_from(Tema)
            .outerjoin(PraticaTema, and_(PraticaTema.tema_id == Tema.id, PraticaTema.stato == StatoTema.confermato,
                                         PraticaTema.pratica_id.in_(select(vis.c.id))))
            .where(Tema.attivo).group_by(Tema.id).order_by(n.desc(), Tema.ordine))
    if limite:
        stmt = stmt.limit(limite)
    return [FascicoloOut(codice=c, nome=nome, pratiche=k) for c, nome, k in db.execute(stmt).all()]


@router.get("/fascicoli", response_model=list[FascicoloOut])
def fascicoli(utente: Utente = Depends(smistatore_o_operatore), db: Session = Depends(get_db)) -> list[FascicoloOut]:
    """Temi con il numero di pratiche (che l'utente vede) in cui il tema è confermato."""
    elenco = _conteggi_fascicoli(db, utente)
    return sorted(elenco, key=lambda f: db.execute(select(Tema.ordine).where(Tema.codice == f.codice)).scalar_one())


@router.get("/fascicoli/{codice}/pratiche", response_model=Pagina)
def pratiche_fascicolo(codice: str, page: int = Query(default=1, ge=1), per_page: int = Query(default=25, ge=1, le=100),
                       utente: Utente = Depends(smistatore_o_operatore), db: Session = Depends(get_db)) -> Pagina:
    """Pratiche con il tema confermato, in ordine di tempo (il percorso del fascicolo)."""
    tema = db.execute(select(Tema).where(Tema.codice == codice, Tema.attivo)).scalar_one_or_none()
    if tema is None:
        raise HTTPException(404, "Fascicolo non trovato")
    q = pratiche_visibili(utente).where(exists().where(
        PraticaTema.pratica_id == Pratica.id, PraticaTema.tema_id == tema.id, PraticaTema.stato == StatoTema.confermato))
    totale = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    giorno = func.coalesce(Pratica.data_protocollo, func.date(Pratica.creata_il))
    righe = db.execute(q.order_by(giorno, Pratica.creata_il, Pratica.id).limit(per_page).offset((page - 1) * per_page)).scalars().all()
    return Pagina(items=arricchisci(db, list(righe)), total=totale, page=page, per_page=per_page)


@router.get("/home", response_model=HomeOut)
def home(utente: Utente = Depends(smistatore_o_operatore), db: Session = Depends(get_db)) -> HomeOut:
    vis = pratiche_visibili(utente)

    def conta(*cond) -> int:
        return db.execute(select(func.count()).select_from(vis.where(*cond).subquery())).scalar_one()

    # «senza riscontro»: esposti in lavorazione senza una pratica `riscontro_ats` collegata
    # (stesso protocollo, o collegamento manuale), la stessa regola del percorso.
    r2 = aliased(Pratica)
    manuale = exists().where(Collegamento.rimosso_il.is_(None), or_(
        and_(Collegamento.pratica_da_id == Pratica.id, Collegamento.pratica_a_id == r2.id),
        and_(Collegamento.pratica_da_id == r2.id, Collegamento.pratica_a_id == Pratica.id)))
    riscontro = exists().where(r2.tipo == "riscontro_ats", r2.id != Pratica.id,
                               or_(and_(Pratica.chiave_protocollo.is_not(None),
                                        r2.chiave_protocollo == Pratica.chiave_protocollo), manuale))
    incerta = exists().where(vista_analisi_principale.c.pratica_id == Pratica.id,
                             vista_analisi_principale.c.lettura_incerta)
    dis = exists().where(vista_disaccordo.c.pratica_id == Pratica.id, vista_disaccordo.c.in_disaccordo)

    contatori = {
        "da_validare": conta(Pratica.stato == Stato.DA_VALIDARE),
        "in_lavorazione": conta(Pratica.stato == Stato.IN_LAVORAZIONE),
        "lettura_incerta": conta(incerta, Pratica.stato.in_(STATI_APERTI)),
        "senza_riscontro": conta(Pratica.tipo == "esposto", Pratica.stato == Stato.IN_LAVORAZIONE, ~riscontro),
    }
    if utente.ruolo == Ruolo.smistatore:
        contatori["da_smistare"] = conta(Pratica.stato == Stato.DA_SMISTARE)

    ultimi = db.execute(vis.where(Pratica.stato == Stato.DA_VALIDARE)
                        .order_by(Pratica.aggiornata_il.desc(), Pratica.id).limit(5)).scalars().all()
    in_dis = db.execute(vis.where(dis).order_by(Pratica.aggiornata_il.desc(), Pratica.id).limit(5)).scalars().all()
    return HomeOut(contatori=contatori, ultimi_arrivi=arricchisci(db, list(ultimi)),
                   fascicoli_piu_attivi=_conteggi_fascicoli(db, utente, limite=5),
                   disaccordo=DisaccordoHome(totale=conta(dis), pratiche=arricchisci(db, list(in_dis))))


# --- configurazione in sola lettura (S, O, A) ------------------------------------------------------

@router.get("/vocabolari")
def vocabolari(_: Utente = Depends(utente_corrente), db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    """Elenchi attuali dei vocabolari ATS. L'elenco storico degli ambiti serve solo all'importazione."""
    out: dict[str, list[dict]] = {}
    for v in db.execute(select(VoceVocabolario).where(VoceVocabolario.attivo, VoceVocabolario.elenco == "attuale")
                        .order_by(VoceVocabolario.vocabolario, VoceVocabolario.ordine)).scalars():
        out.setdefault(v.vocabolario, []).append({"codice": v.codice, "etichetta": v.etichetta})
    return out


@router.get("/temi", response_model=list[TemaCatalogoOut])
def temi(_: Utente = Depends(utente_corrente), db: Session = Depends(get_db)) -> list[Tema]:
    return list(db.execute(select(Tema).where(Tema.attivo).order_by(Tema.ordine, Tema.codice)).scalars())


@router.get("/tipi-collegamento", response_model=list[TipoCollegamentoOut])
def tipi_collegamento(_: Utente = Depends(utente_corrente), db: Session = Depends(get_db)) -> list[TipoCollegamento]:
    return list(db.execute(select(TipoCollegamento).order_by(TipoCollegamento.codice)).scalars())
