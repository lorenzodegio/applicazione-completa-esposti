"""Caricamento documenti e risultati del motore (piano, sezione 7: Documenti e motore)."""
import datetime as dt
import json
import mimetypes
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from documenti import ArchivioDocumenti, ErroreArchivio

from ..analisi import risultati_documento, stato_analisi_documento
from ..archivio import get_archivio
from ..coda import accoda
from ..config import get_settings
from ..db import get_db
from ..deps import smistatore_o_operatore, solo_smistatore
from ..enums import Canale, Stato, StatoLavoro, TipoArchivio
from ..models import CambioStato, Documento, LavoroMotore, Pratica, Utente
from ..numerazione import prossimo_numero
from ..permessi import carica_pratica
from ..registro import registra
from ..schemas import AnalisiOut, DocumentoOut, LavoroOut, NuovaPraticaOut, PraticaOut

router = APIRouter(tags=["documenti e motore"])


def _carica_documento(db: Session, utente: Utente, documento_id: uuid.UUID) -> tuple[Documento, Pratica]:
    doc = db.get(Documento, documento_id)
    if doc is None:
        raise HTTPException(404, "Documento non trovato")
    return doc, carica_pratica(db, utente, doc.pratica_id)  # stesso perimetro della pratica: 404 se non visibile


def _salva_file(db: Session, archivio: ArchivioDocumenti, pratica: Pratica, f: UploadFile, utente: Utente) -> Documento:
    cfg = get_settings()
    nome = (f.filename or "documento").replace("\\", "/").split("/")[-1][:500] or "documento"
    doc_id = uuid.uuid4()
    rif = archivio.salva(pratica.id, nome, f.file, id_documento=doc_id)
    if rif.dimensione == 0:
        archivio.elimina(rif.id_archivio)
        raise HTTPException(422, f"Il file «{nome}» è vuoto")
    if rif.dimensione > cfg.max_mb_per_file * 1024 * 1024:
        archivio.elimina(rif.id_archivio)
        raise HTTPException(413, f"Il file «{nome}» supera {cfg.max_mb_per_file} MB")
    doc = Documento(id=doc_id, pratica_id=pratica.id, nome_file=nome,
                    tipo_mime=f.content_type or mimetypes.guess_type(nome)[0], dimensione=rif.dimensione,
                    sha256=rif.sha256, archivio=TipoArchivio(rif.archivio), id_archivio=rif.id_archivio,
                    caricato_da=utente.id,
                    caricato_il=dt.datetime.now(dt.timezone.utc))  # non now() del DB: stesso istante in una transazione
    db.add(doc)
    db.flush()
    registra(db, utente_id=utente.id, azione="documento.carica", oggetto_tipo="documento", oggetto_id=doc.id,
             pratica_id=pratica.id, dettagli={"sha256": doc.sha256, "dimensione": doc.dimensione})
    accoda(db, doc, utente.id)
    return doc


def _doc_out(db: Session, doc: Documento, pratica: Pratica) -> DocumentoOut:
    out = DocumentoOut.model_validate(doc)
    out.principale = pratica.documento_principale_id == doc.id
    out.analisi = stato_analisi_documento(db, doc.id)
    return out


def _controlla_numero(files: list[UploadFile]) -> None:
    if not files:
        raise HTTPException(422, "Serve almeno un documento")
    if len(files) > get_settings().max_file_per_richiesta:
        raise HTTPException(422, f"Al massimo {get_settings().max_file_per_richiesta} documenti per volta")


@router.post("/pratiche", response_model=NuovaPraticaOut, status_code=201)
def nuova_pratica(
    files: list[UploadFile] = File(...),
    titolo: str | None = Form(default=None, max_length=300),
    protocollo: str | None = Form(default=None, max_length=64),
    comune: str | None = Form(default=None, max_length=200),
    utente: Utente = Depends(solo_smistatore),
    db: Session = Depends(get_db),
    archivio: ArchivioDocumenti = Depends(get_archivio),
) -> NuovaPraticaOut:
    """Caricamento a mano: la pratica nasce IN_ANALISI e ogni documento va in coda al motore."""
    _controlla_numero(files)
    primo = (files[0].filename or "documento").rsplit(".", 1)[0][:300]
    pratica = Pratica(numero=prossimo_numero(db), protocollo=protocollo or None, tipo="esposto",
                      titolo=titolo or primo, comune=comune or None, canale=Canale.caricamento_manuale,
                      stato=Stato.IN_ANALISI)
    db.add(pratica)
    db.flush()
    db.add(CambioStato(pratica_id=pratica.id, da_stato=None, a_stato=Stato.IN_ANALISI, utente_id=utente.id))
    registra(db, utente_id=utente.id, azione="pratica.crea", oggetto_tipo="pratica", oggetto_id=pratica.id,
             pratica_id=pratica.id, dettagli={"canale": "caricamento_manuale", "documenti": len(files)})
    try:
        docs = [_salva_file(db, archivio, pratica, f, utente) for f in files]
    except HTTPException:
        db.rollback()
        raise
    pratica.documento_principale_id = docs[0].id
    db.commit()
    return NuovaPraticaOut(pratica=PraticaOut.model_validate(pratica),
                           documenti=[_doc_out(db, d, pratica) for d in docs])


@router.get("/pratiche/{pratica_id}/documenti", response_model=list[DocumentoOut])
def elenco_documenti(pratica_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                     db: Session = Depends(get_db)) -> list[DocumentoOut]:
    pratica = carica_pratica(db, utente, pratica_id)
    docs = db.execute(select(Documento).where(Documento.pratica_id == pratica.id)
                      .order_by(Documento.caricato_il, Documento.id)).scalars().all()
    return [_doc_out(db, d, pratica) for d in docs]


@router.post("/pratiche/{pratica_id}/documenti", response_model=list[DocumentoOut], status_code=201)
def aggiungi_documenti(pratica_id: uuid.UUID, files: list[UploadFile] = File(...),
                       utente: Utente = Depends(smistatore_o_operatore), db: Session = Depends(get_db),
                       archivio: ArchivioDocumenti = Depends(get_archivio)) -> list[DocumentoOut]:
    _controlla_numero(files)
    pratica = carica_pratica(db, utente, pratica_id, per_modifica=True)
    try:
        docs = [_salva_file(db, archivio, pratica, f, utente) for f in files]
    except HTTPException:
        db.rollback()
        raise
    if pratica.documento_principale_id is None:
        pratica.documento_principale_id = docs[0].id
    db.commit()
    return [_doc_out(db, d, pratica) for d in docs]


@router.get("/documenti/{documento_id}/analisi", response_model=list[AnalisiOut])
def analisi_documento(documento_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                      db: Session = Depends(get_db)) -> list[AnalisiOut]:
    doc, _ = _carica_documento(db, utente, documento_id)
    return risultati_documento(db, doc.id)  # ultimo per primo


@router.post("/documenti/{documento_id}/analisi", response_model=LavoroOut, status_code=202)
def rilancia_analisi(documento_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                     db: Session = Depends(get_db)) -> LavoroMotore:
    doc, pratica = _carica_documento(db, utente, documento_id)
    aperto = db.execute(select(LavoroMotore.id).where(
        LavoroMotore.documento_id == doc.id,
        LavoroMotore.stato.in_([StatoLavoro.in_coda, StatoLavoro.in_corso])).limit(1)).first()
    if aperto:
        raise HTTPException(409, "Per questo documento c'è già un'analisi in corso")
    lavoro = accoda(db, doc, utente.id)
    db.commit()
    return lavoro


@router.get("/lavori/{lavoro_id}", response_model=LavoroOut)
def lavoro(lavoro_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
           db: Session = Depends(get_db)) -> LavoroMotore:
    l = db.get(LavoroMotore, lavoro_id)
    if l is None:
        raise HTTPException(404, "Lavoro non trovato")
    carica_pratica(db, utente, l.pratica_id)
    return l


@router.get("/documenti/{documento_id}/testo")
def testo_documento(documento_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                    db: Session = Depends(get_db), archivio: ArchivioDocumenti = Depends(get_archivio)) -> dict:
    doc, pratica = _carica_documento(db, utente, documento_id)
    if not doc.id_archivio_testo:
        raise HTTPException(404, "Testo non ancora disponibile")
    try:
        with archivio.apri(doc.id_archivio_testo) as f:
            dati = json.load(f)
    except ErroreArchivio:
        raise HTTPException(404, "Testo non disponibile in archivio")
    registra(db, utente_id=utente.id, azione="documento.testo", oggetto_tipo="documento", oggetto_id=doc.id,
             pratica_id=pratica.id)
    db.commit()
    return {"documento_id": str(doc.id), "pagine": dati["pagine"]}


@router.get("/documenti/{documento_id}/contenuto")
def contenuto_documento(documento_id: uuid.UUID, utente: Utente = Depends(smistatore_o_operatore),
                        db: Session = Depends(get_db), archivio: ArchivioDocumenti = Depends(get_archivio)):
    doc, pratica = _carica_documento(db, utente, documento_id)
    try:
        f = archivio.apri(doc.id_archivio)
    except ErroreArchivio:
        raise HTTPException(404, "Documento non disponibile in archivio")
    registra(db, utente_id=utente.id, azione="documento.apri", oggetto_tipo="documento", oggetto_id=doc.id,
             pratica_id=pratica.id)
    db.commit()
    pdf = doc.tipo_mime == "application/pdf"
    nome = doc.nome_file.replace('"', "").replace("\r", "").replace("\n", "")
    return StreamingResponse(iter(lambda: f.read(1024 * 1024), b""),
                             media_type=doc.tipo_mime or "application/octet-stream",
                             headers={"Content-Disposition": f'{"inline" if pdf else "attachment"}; filename="{nome}"',
                                      "X-Content-Type-Options": "nosniff"})
