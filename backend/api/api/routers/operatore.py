"""Lavoro dell'operatore sulla pratica: valutazione, validazione, temi, attività (piano 7)."""
import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import smistatore_o_operatore
from ..enums import Stato, StatoAttivita, StatoTema
from ..models import Attivita, CambioStato, Pratica, PraticaTema, Utente, Valutazione
from ..permessi import carica_pratica
from ..registro import registra
from ..schemas import (
    AttivitaIn, AttivitaOut, AttivitaPatch, PraticaOut, TemaDecisione, TemaOut, TemiIn, ValidazioneIn,
    ValutazioneIn, ValutazioneOut, ValutazioneVista,
)
from ..valutazione import (
    applica_temi, leggi_valutazione_vista, salva_valutazione, temi_pratica, valida, vocabolari_attuali,
)

router = APIRouter(tags=["operatore"])

STATI_MODIFICABILI = (Stato.DA_VALIDARE, Stato.IN_LAVORAZIONE)


def _aggiorna(pratica: Pratica) -> None:
    pratica.versione += 1
    pratica.aggiornata_il = dt.datetime.now(dt.timezone.utc)


# --- valutazione ----------------------------------------------------------------------

@router.get("/pratiche/{pratica_id}/valutazione", response_model=ValutazioneVista)
def leggi_valutazione(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                      db: Session = Depends(get_db)) -> ValutazioneVista:
    return leggi_valutazione_vista(db, carica_pratica(db, utente, pratica_id))


@router.put("/pratiche/{pratica_id}/valutazione", response_model=ValutazioneOut)
def scrivi_valutazione(pratica_id: uuid.UUID, dati: ValutazioneIn, utente: Utente = Depends(smistatore_o_operatore),
                       db: Session = Depends(get_db)) -> Valutazione:
    """Salva (o aggiorna) la valutazione senza cambiare lo stato; per validare c'è /validazione."""
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    if pratica.stato not in STATI_MODIFICABILI:
        raise HTTPException(409, f"Una pratica in stato {pratica.stato} non ha una valutazione modificabile")
    valida(db, dati, per_conferma=dati.compilata)
    v = salva_valutazione(db, pratica, utente, dati, azione_registro="valutazione.salva")
    db.commit()
    return v


# --- validazione (Inbox) ---------------------------------------------------------------

@router.post("/pratiche/{pratica_id}/validazione", response_model=PraticaOut)
def valida_pratica(pratica_id: uuid.UUID, dati: ValidazioneIn, utente: Utente = Depends(smistatore_o_operatore),
                   db: Session = Depends(get_db)) -> Pratica:
    """Valutazione compilata → IN_LAVORAZIONE. La decide la persona; i temi proposti non toccati diventano confermati."""
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    if pratica.versione != dati.versione:
        raise HTTPException(409, "La pratica è stata modificata nel frattempo: ricarica e riprova")
    if pratica.stato != Stato.DA_VALIDARE:
        raise HTTPException(409, f"Una pratica in stato {pratica.stato} non si può validare")
    dati.valutazione.compilata = True
    valida(db, dati.valutazione, per_conferma=True)

    # I temi proposti dall'IA che l'operatore non tocca si considerano accettati da chi valida.
    decisi = {d.codice for d in dati.temi}
    impliciti = [pt.tema.codice for pt in db.execute(select(PraticaTema).where(
        PraticaTema.pratica_id == pratica.id, PraticaTema.stato == StatoTema.proposto)).scalars()
        if pt.tema.codice not in decisi]

    salva_valutazione(db, pratica, utente, dati.valutazione, azione_registro="valutazione.conferma")
    cambi = applica_temi(db, pratica, utente, [*dati.temi, *(TemaDecisione(codice=c, stato=StatoTema.confermato)
                                                              for c in impliciti)])
    for c in impliciti:
        cambi[c]["implicito"] = True
    if cambi:
        registra(db, utente_id=utente.id, azione="temi.decidi", oggetto_tipo="pratica", oggetto_id=pratica.id,
                 pratica_id=pratica.id, dettagli={"temi": cambi})
    db.add(CambioStato(pratica_id=pratica.id, da_stato=pratica.stato, a_stato=Stato.IN_LAVORAZIONE,
                       utente_id=utente.id))
    pratica.stato = Stato.IN_LAVORAZIONE
    _aggiorna(pratica)
    registra(db, utente_id=utente.id, azione="pratica.valida", oggetto_tipo="pratica", oggetto_id=pratica.id,
             pratica_id=pratica.id, dettagli={"da": "DA_VALIDARE", "a": "IN_LAVORAZIONE"})
    db.commit()
    return pratica


# --- temi ---------------------------------------------------------------------------------

@router.get("/pratiche/{pratica_id}/temi", response_model=list[TemaOut])
def elenco_temi(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                db: Session = Depends(get_db)) -> list[TemaOut]:
    return temi_pratica(db, carica_pratica(db, utente, pratica_id).id)


@router.put("/pratiche/{pratica_id}/temi", response_model=list[TemaOut])
def decidi_temi(pratica_id: uuid.UUID, dati: TemiIn, utente: Utente = Depends(smistatore_o_operatore),
                db: Session = Depends(get_db)) -> list[TemaOut]:
    """Conferma, scarta o aggiunge temi (anche dopo la validazione)."""
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    if pratica.stato not in STATI_MODIFICABILI:
        raise HTTPException(409, f"Una pratica in stato {pratica.stato} non ha temi modificabili")
    cambi = applica_temi(db, pratica, utente, dati.temi)
    if cambi:
        registra(db, utente_id=utente.id, azione="temi.decidi", oggetto_tipo="pratica", oggetto_id=pratica.id,
                 pratica_id=pratica.id, dettagli={"temi": cambi})
    db.commit()
    return temi_pratica(db, pratica.id)


# --- attività (le azioni dell'ufficio) --------------------------------------------------------

TRANSIZIONI_ATTIVITA = {
    StatoAttivita.prevista: {StatoAttivita.in_corso, StatoAttivita.conclusa, StatoAttivita.annullata},
    StatoAttivita.in_corso: {StatoAttivita.conclusa, StatoAttivita.annullata},
    StatoAttivita.conclusa: set(),
    StatoAttivita.annullata: set(),
}


def _controlla_tipo(db: Session, tipo: str) -> None:
    if tipo not in vocabolari_attuali(db).get("azione", set()):
        raise HTTPException(422, f"Tipo di attività «{tipo}» non presente nel vocabolario")


@router.get("/pratiche/{pratica_id}/attivita", response_model=list[AttivitaOut])
def elenco_attivita(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                    db: Session = Depends(get_db)) -> list[Attivita]:
    pratica = carica_pratica(db, utente, pratica_id)
    return list(db.execute(select(Attivita).where(Attivita.pratica_id == pratica.id)
                           .order_by(Attivita.creata_il, Attivita.id)).scalars())


@router.post("/pratiche/{pratica_id}/attivita", response_model=AttivitaOut, status_code=201)
def nuova_attivita(pratica_id: uuid.UUID, dati: AttivitaIn, utente: Utente = Depends(smistatore_o_operatore),
                   db: Session = Depends(get_db)) -> Attivita:
    pratica = carica_pratica(db, utente, pratica_id)
    if pratica.stato != Stato.IN_LAVORAZIONE:
        raise HTTPException(409, "Le attività si aggiungono a una pratica in lavorazione")
    _controlla_tipo(db, dati.tipo)
    a = Attivita(pratica_id=pratica.id, tipo=dati.tipo, stato=StatoAttivita.prevista,
                 data_prevista=dati.data_prevista, descrizione=dati.descrizione, creata_da=utente.id)
    db.add(a)
    db.flush()
    registra(db, utente_id=utente.id, azione="attivita.crea", oggetto_tipo="attivita", oggetto_id=a.id,
             pratica_id=pratica.id, dettagli={"tipo": a.tipo})
    db.commit()
    return a


@router.patch("/attivita/{attivita_id}", response_model=AttivitaOut)
def modifica_attivita(attivita_id: uuid.UUID, dati: AttivitaPatch, utente: Utente = Depends(smistatore_o_operatore),
                      db: Session = Depends(get_db)) -> Attivita:
    a = db.get(Attivita, attivita_id)
    if a is None:
        raise HTTPException(404, "Attività non trovata")
    pratica = carica_pratica(db, utente, a.pratica_id)   # stesso perimetro della pratica
    if pratica.stato != Stato.IN_LAVORAZIONE:
        raise HTTPException(409, "Le attività si modificano su una pratica in lavorazione")
    if a.stato in (StatoAttivita.conclusa, StatoAttivita.annullata):
        raise HTTPException(409, f"Un'attività {a.stato} non si modifica")
    prima = a.stato
    if dati.stato is not None and dati.stato != a.stato:
        if dati.stato not in TRANSIZIONI_ATTIVITA[a.stato]:
            raise HTTPException(409, f"Transizione {a.stato} → {dati.stato} non ammessa")
        a.stato = dati.stato
        if dati.stato == StatoAttivita.conclusa:
            a.data_conclusione = dati.data_conclusione or dt.date.today()
    for campo in ("data_prevista", "descrizione"):
        if campo in dati.model_fields_set:
            setattr(a, campo, getattr(dati, campo))
    a.aggiornata_il = dt.datetime.now(dt.timezone.utc)
    registra(db, utente_id=utente.id, azione="attivita.modifica", oggetto_tipo="attivita", oggetto_id=a.id,
             pratica_id=pratica.id, dettagli={"tipo": a.tipo, "stato": {"prima": prima.value, "dopo": a.stato.value}})
    db.commit()
    return a
