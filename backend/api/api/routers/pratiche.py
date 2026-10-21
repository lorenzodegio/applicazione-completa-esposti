import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from ..analisi import analisi_pratica
from ..arricchimento import arricchisci
from ..db import get_db
from ..deps import smistatore_o_operatore, solo_operatore, solo_smistatore
from ..enums import OrigineValutazione, Ruolo, Stato, StatoTema
from ..models import (
    Assegnazione, CambioStato, NotaInterna, Pratica, PraticaTema, RegistroAzioni, Tema, Ufficio, Utente,
    Valutazione, vista_analisi_principale, vista_disaccordo,
)
from ..permessi import carica_pratica, pratiche_visibili
from ..registro import registra
from ..schemas import (
    AssegnazioneIn, CambioStatoIn, NotaIn, NotaOut, Pagina, PraticaOut, PraticaPatch,
    PraticaDettaglio, RestituzioneIn, VoceRegistro, VoceStorico,
)
from ..transizioni import regola
from ..valutazione import disaccordo_per, leggi_valutazione_vista, temi_pratica

router = APIRouter(tags=["pratiche"])


def _controlla_versione(pratica: Pratica, versione: int) -> None:
    if pratica.versione != versione:
        raise HTTPException(409, "La pratica è stata modificata nel frattempo: ricarica e riprova")


def _aggiorna(pratica: Pratica) -> None:
    pratica.versione += 1
    pratica.aggiornata_il = dt.datetime.now(dt.timezone.utc)


def _cambia_stato(db: Session, pratica: Pratica, a: Stato, utente_id, motivo: str | None) -> None:
    db.add(CambioStato(pratica_id=pratica.id, da_stato=pratica.stato, a_stato=a,
                       utente_id=utente_id, motivo=motivo))
    pratica.stato = a


def _pagina(db: Session, q, page: int, per_page: int, *, ordine) -> Pagina:
    totale = db.execute(select(func.count()).select_from(q.order_by(None).subquery())).scalar_one()
    righe = db.execute(q.order_by(*ordine).limit(per_page).offset((page - 1) * per_page)).scalars().all()
    return Pagina(items=arricchisci(db, list(righe)), total=totale, page=page, per_page=per_page)


def _escape_like(testo: str) -> str:
    return testo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --- Elenchi -----------------------------------------------------------------

@router.get("/pratiche", response_model=Pagina)
def elenco(
    testo: str | None = Query(default=None, max_length=100),
    stato: Stato | None = None,
    tema: str | None = Query(default=None, max_length=64),
    tipo: str | None = Query(default=None, max_length=64),
    con_valutazione_ats: bool | None = None,
    disaccordo: bool | None = None,
    lettura_incerta: bool | None = None,
    dal: dt.date | None = None,
    al: dt.date | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
    utente: Utente = Depends(smistatore_o_operatore),
    db: Session = Depends(get_db),
) -> Pagina:
    q = pratiche_visibili(utente)
    if testo:
        t = f"%{_escape_like(testo)}%"
        q = q.where(or_(Pratica.protocollo.ilike(t), Pratica.comune.ilike(t),
                        Pratica.titolo.ilike(t), Pratica.numero.ilike(t)))
    if stato:
        q = q.where(Pratica.stato == stato)
    if tipo:
        q = q.where(Pratica.tipo == tipo)
    if tema:  # fascicolo: conta solo il tema confermato
        q = q.where(exists().where(PraticaTema.pratica_id == Pratica.id, PraticaTema.stato == StatoTema.confermato,
                                   PraticaTema.tema_id == Tema.id, Tema.codice == tema))
    if con_valutazione_ats is not None:
        ats = exists().where(Valutazione.pratica_id == Pratica.id, Valutazione.origine == OrigineValutazione.import_ats)
        q = q.where(ats if con_valutazione_ats else ~ats)
    if disaccordo is not None:
        dis = exists().where(vista_disaccordo.c.pratica_id == Pratica.id, vista_disaccordo.c.in_disaccordo)
        q = q.where(dis if disaccordo else ~dis)
    if lettura_incerta is not None:
        inc = exists().where(vista_analisi_principale.c.pratica_id == Pratica.id,
                             vista_analisi_principale.c.lettura_incerta)
        q = q.where(inc if lettura_incerta else ~inc)
    giorno = func.coalesce(Pratica.data_protocollo, func.date(Pratica.creata_il))
    if dal:
        q = q.where(giorno >= dal)
    if al:
        q = q.where(giorno <= al)
    return _pagina(db, q, page, per_page, ordine=(Pratica.creata_il.desc(), Pratica.id))


@router.get("/smistamento", response_model=Pagina)
def smistamento(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
    utente: Utente = Depends(solo_smistatore),
    db: Session = Depends(get_db),
) -> Pagina:
    # L'ufficio suggerito arriva con la proposta del motore (fase 2/5).
    q = pratiche_visibili(utente).where(Pratica.stato == Stato.DA_SMISTARE)
    return _pagina(db, q, page, per_page, ordine=(Pratica.creata_il, Pratica.id))


@router.get("/inbox", response_model=Pagina)
def inbox(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=100),
    utente: Utente = Depends(smistatore_o_operatore),
    db: Session = Depends(get_db),
) -> Pagina:
    q = pratiche_visibili(utente).where(Pratica.stato == Stato.DA_VALIDARE)
    return _pagina(db, q, page, per_page, ordine=(Pratica.creata_il, Pratica.id))  # ordine di arrivo


# --- Dettaglio e modifica ------------------------------------------------------

@router.get("/pratiche/{pratica_id}", response_model=PraticaDettaglio)
def dettaglio(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
              db: Session = Depends(get_db)) -> PraticaDettaglio:
    pratica = carica_pratica(db, utente, pratica_id)
    stato, analisi, avvisi = analisi_pratica(db, pratica)
    out = PraticaDettaglio.model_validate(pratica)
    out.stato_analisi, out.analisi, out.avvisi = stato, analisi, avvisi
    out.temi = temi_pratica(db, pratica.id)
    out.valutazione = leggi_valutazione_vista(db, pratica)
    out.disaccordo = disaccordo_per(db, [pratica.id]).get(pratica.id, [])
    out.n_collegate = arricchisci(db, [pratica])[0].n_collegate
    return out


@router.patch("/pratiche/{pratica_id}", response_model=PraticaOut)
def modifica(pratica_id: uuid.UUID, dati: PraticaPatch, utente: Utente = Depends(smistatore_o_operatore),
             db: Session = Depends(get_db)) -> Pratica:
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    _controlla_versione(pratica, dati.versione)
    prima, dopo = {}, {}
    for campo in ("titolo", "protocollo", "comune"):
        if campo in dati.model_fields_set and getattr(dati, campo) != getattr(pratica, campo):
            prima[campo], dopo[campo] = getattr(pratica, campo), getattr(dati, campo)
            setattr(pratica, campo, getattr(dati, campo))
    if dopo:
        _aggiorna(pratica)
        registra(db, utente_id=utente.id, azione="pratica.modifica", oggetto_tipo="pratica",
                 oggetto_id=pratica.id, pratica_id=pratica.id, dettagli={"prima": prima, "dopo": dopo})
    db.commit()
    return pratica


# --- Assegnazione, restituzione, stato ------------------------------------------

@router.post("/pratiche/{pratica_id}/assegnazione", response_model=PraticaOut)
def assegna(pratica_id: uuid.UUID, dati: AssegnazioneIn, utente: Utente = Depends(solo_smistatore),
            db: Session = Depends(get_db)) -> Pratica:
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    _controlla_versione(pratica, dati.versione)
    if pratica.stato not in (Stato.DA_SMISTARE, Stato.DA_VALIDARE):
        raise HTTPException(409, f"Una pratica in stato {pratica.stato} non si può assegnare")
    ufficio = db.get(Ufficio, dati.ufficio_id)
    if ufficio is None or not ufficio.attivo:
        raise HTTPException(422, "Ufficio non valido")
    riassegnazione = pratica.stato == Stato.DA_VALIDARE
    if riassegnazione:
        if not dati.motivo or not dati.motivo.strip():
            raise HTTPException(422, "Il motivo è obbligatorio per le riassegnazioni")
        if pratica.ufficio_id == ufficio.id:
            raise HTTPException(422, "La pratica è già assegnata a questo ufficio")

    precedente = pratica.ufficio_id
    db.add(Assegnazione(pratica_id=pratica.id, ufficio_id=ufficio.id, ufficio_precedente_id=precedente,
                        assegnata_da=utente.id, motivo=dati.motivo, da_proposta_ia=dati.da_proposta_ia))
    if not riassegnazione:
        _cambia_stato(db, pratica, Stato.DA_VALIDARE, utente.id, None)
    pratica.ufficio = ufficio  # l'ufficio precedente perde subito la visibilità
    _aggiorna(pratica)
    registra(db, utente_id=utente.id,
             azione="pratica.riassegna" if riassegnazione else "pratica.assegna",
             oggetto_tipo="pratica", oggetto_id=pratica.id, pratica_id=pratica.id,
             dettagli={"ufficio_id": str(ufficio.id),
                       "ufficio_precedente_id": str(precedente) if precedente else None,
                       "da_proposta_ia": dati.da_proposta_ia})
    db.commit()
    return pratica


@router.post("/pratiche/{pratica_id}/restituzione", response_model=PraticaOut)
def restituisci(pratica_id: uuid.UUID, dati: RestituzioneIn, utente: Utente = Depends(solo_operatore),
                db: Session = Depends(get_db)) -> Pratica:
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    _controlla_versione(pratica, dati.versione)
    r = regola(pratica.stato, Stato.DA_SMISTARE)
    if r is None or utente.ruolo not in r.ruoli:
        raise HTTPException(409, f"Una pratica in stato {pratica.stato} non si può restituire")
    if not dati.motivo.strip():
        raise HTTPException(422, "Il motivo è obbligatorio")
    precedente = pratica.ufficio_id
    _cambia_stato(db, pratica, Stato.DA_SMISTARE, utente.id, dati.motivo)
    pratica.ufficio = None  # torna allo smistatore: l'ufficio non la vede più
    _aggiorna(pratica)
    registra(db, utente_id=utente.id, azione="pratica.restituisci", oggetto_tipo="pratica",
             oggetto_id=pratica.id, pratica_id=pratica.id,
             dettagli={"ufficio_precedente_id": str(precedente)})
    db.commit()
    return pratica


@router.post("/pratiche/{pratica_id}/stato", response_model=PraticaOut)
def cambia_stato(pratica_id: uuid.UUID, dati: CambioStatoIn, utente: Utente = Depends(smistatore_o_operatore),
                 db: Session = Depends(get_db)) -> Pratica:
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    _controlla_versione(pratica, dati.versione)
    r = regola(pratica.stato, dati.a_stato)
    if r is None or not r.generica:
        raise HTTPException(409, f"Transizione {pratica.stato} → {dati.a_stato} non ammessa")
    if utente.ruolo not in r.ruoli:
        raise HTTPException(403, "Operazione non consentita al tuo ruolo")
    if r.motivo_obbligatorio and not (dati.motivo and dati.motivo.strip()):
        raise HTTPException(422, "Il motivo è obbligatorio per questa transizione")
    da = pratica.stato
    _cambia_stato(db, pratica, dati.a_stato, utente.id, dati.motivo)
    _aggiorna(pratica)
    registra(db, utente_id=utente.id, azione="pratica.cambia_stato", oggetto_tipo="pratica",
             oggetto_id=pratica.id, pratica_id=pratica.id,
             dettagli={"da": da.value, "a": dati.a_stato.value})
    db.commit()
    return pratica


# --- Note, storico, registro ------------------------------------------------------

@router.post("/pratiche/{pratica_id}/note", response_model=NotaOut, status_code=201)
def nuova_nota(pratica_id: uuid.UUID, dati: NotaIn, utente: Utente = Depends(smistatore_o_operatore),
               db: Session = Depends(get_db)) -> NotaInterna:
    pratica = carica_pratica(db, utente, pratica_id)
    nota = NotaInterna(pratica_id=pratica.id, autore_id=utente.id, testo=dati.testo)
    db.add(nota)
    db.flush()
    registra(db, utente_id=utente.id, azione="nota.crea", oggetto_tipo="nota_interna",
             oggetto_id=nota.id, pratica_id=pratica.id)  # niente testo nel registro
    db.commit()
    return nota


@router.get("/pratiche/{pratica_id}/note", response_model=list[NotaOut])
def note(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
         db: Session = Depends(get_db)) -> list[NotaInterna]:
    pratica = carica_pratica(db, utente, pratica_id)
    return list(db.execute(select(NotaInterna).where(NotaInterna.pratica_id == pratica.id)
                           .order_by(NotaInterna.creata_il, NotaInterna.id)).scalars())


@router.get("/pratiche/{pratica_id}/storico", response_model=list[VoceStorico])
def storico(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
            db: Session = Depends(get_db)) -> list[VoceStorico]:
    pratica = carica_pratica(db, utente, pratica_id)
    voci: list[VoceStorico] = []
    for a in db.execute(select(Assegnazione).where(Assegnazione.pratica_id == pratica.id)).scalars():
        voci.append(VoceStorico(tipo="assegnazione", il=a.assegnata_il, utente_id=a.assegnata_da, dettagli={
            "ufficio_id": str(a.ufficio_id),
            "ufficio_precedente_id": str(a.ufficio_precedente_id) if a.ufficio_precedente_id else None,
            "motivo": a.motivo, "da_proposta_ia": a.da_proposta_ia}))
    for c in db.execute(select(CambioStato).where(CambioStato.pratica_id == pratica.id)).scalars():
        voci.append(VoceStorico(tipo="cambio_stato", il=c.il, utente_id=c.utente_id, dettagli={
            "da": c.da_stato.value if c.da_stato else None, "a": c.a_stato.value, "motivo": c.motivo}))
    return sorted(voci, key=lambda v: v.il)


@router.get("/pratiche/{pratica_id}/registro", response_model=list[VoceRegistro])
def registro_pratica(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                     db: Session = Depends(get_db)) -> list[RegistroAzioni]:
    pratica = carica_pratica(db, utente, pratica_id)
    return list(db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == pratica.id)
                           .order_by(RegistroAzioni.id)).scalars())
