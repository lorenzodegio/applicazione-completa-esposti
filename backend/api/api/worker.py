"""Worker della coda: un lavoro alla volta, un solo worker (piano, sezione 4).

    python -m api.worker                # resta in ascolto
    python -m api.worker --una-volta    # svuota la coda ed esce (prove)

Per ogni lavoro: scarico temporaneo → consegna al motore → attesa → salvataggio
(testo accanto al documento, risultato nel database) → conferma al motore →
cancellazione del temporaneo (sempre, anche in caso di errore).
"""
import argparse
import json
import logging
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from documenti import ArchivioDocumenti, ErroreArchivio, RiferimentoArchivio
from motore.client import (
    ClientMotore, MotoreHttp, MotoreIrraggiungibile, MotoreOccupato, MotoreRifiuto,
    RisultatoNonValido, motore_finto_in_processo,
)
from motore.contratto import Risultato

from .archivio import get_archivio
from .config import get_settings
from .db import get_sessionmaker
from .enums import Stato, StatoLavoro
from .models import CambioStato, Documento, LavoroMotore, Pratica, RisultatoMotore
from .registro import registra
from .valutazione import proponi_temi

log = logging.getLogger("worker")


@lru_cache
def get_client() -> ClientMotore:
    url = get_settings().motore_url
    return MotoreHttp(url) if url else motore_finto_in_processo()


@dataclass
class Esito:
    tipo: str                     # completato | errore | ritentato | occupato
    attesa: float = 0.0           # solo per "occupato"
    codice: str | None = None


def _ora():
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc)


# --- cartella temporanea ----------------------------------------------------------------

PREFISSO_TEMP = "esposti-"


def cartella_temporanea() -> str | None:
    """La cartella dei temporanei (ESPOSTI_DIR_TEMPORANEA): si crea se manca. None = quella di sistema."""
    d = get_settings().dir_temporanea
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
    return d


def pulisci_temporanei() -> int:
    """All'avvio: cancella i temporanei rimasti da un worker interrotto (il documento non deve restare qui)."""
    base = Path(cartella_temporanea() or tempfile.gettempdir())
    vecchi = [p for p in base.glob(f"{PREFISSO_TEMP}*") if p.is_dir()]
    for p in vecchi:
        shutil.rmtree(p, ignore_errors=True)
    return len(vecchi)


# --- coda -----------------------------------------------------------------------------

def riprendi_interrotti(db: Session) -> int:
    """Con un solo worker, un lavoro `in_corso` all'avvio è rimasto a metà: torna in coda."""
    interrotti = db.execute(select(LavoroMotore).where(LavoroMotore.stato == StatoLavoro.in_corso)
                            .with_for_update()).scalars().all()
    for lavoro in interrotti:
        lavoro.stato = StatoLavoro.in_coda
        lavoro.tentativi = max(0, lavoro.tentativi - 1)
        registra(db, utente_id=None, azione="motore.riprendi", oggetto_tipo="lavoro_motore",
                 oggetto_id=lavoro.id, pratica_id=lavoro.pratica_id)
    db.commit()
    return len(interrotti)


def prendi_prossimo(db: Session) -> LavoroMotore | None:
    lavoro = db.execute(
        select(LavoroMotore).where(LavoroMotore.stato == StatoLavoro.in_coda)
        .order_by(LavoroMotore.richiesto_il, LavoroMotore.id).limit(1).with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if lavoro is None:
        return None
    lavoro.stato = StatoLavoro.in_corso
    lavoro.tentativi += 1
    lavoro.iniziato_il = _ora()
    db.commit()
    return lavoro


# --- esiti ---------------------------------------------------------------------------------

def _fallisci(db: Session, lavoro: LavoroMotore, codice: str, ritentabile: bool, dettagli: dict | None = None) -> Esito:
    cfg = get_settings()
    d = {"codice": codice, "tentativo": lavoro.tentativi, **(dettagli or {})}
    if ritentabile and lavoro.tentativi < cfg.motore_max_tentativi:
        lavoro.stato = StatoLavoro.in_coda
        registra(db, utente_id=None, azione="motore.ritenta", oggetto_tipo="lavoro_motore",
                 oggetto_id=lavoro.id, pratica_id=lavoro.pratica_id, dettagli=d)
        db.commit()
        return Esito("ritentato", codice=codice)
    lavoro.stato = StatoLavoro.errore
    lavoro.codice_errore = codice
    lavoro.finito_il = _ora()
    registra(db, utente_id=None, azione="motore.errore", oggetto_tipo="lavoro_motore",
             oggetto_id=lavoro.id, pratica_id=lavoro.pratica_id, dettagli=d)
    _concludi_pratica_se_pronta(db, lavoro.pratica_id)
    db.commit()
    return Esito("errore", codice=codice)


def _salva_risultato(db: Session, lavoro: LavoroMotore, doc: Documento, r: Risultato,
                     archivio: ArchivioDocumenti) -> Esito:
    if r.documento.id != str(doc.id) or r.documento.sha256 != doc.sha256:
        return _fallisci(db, lavoro, "risultato_non_coerente", False)
    # testo per pagina: accanto al documento in archivio, non nel database
    testo = json.dumps({"versione_contratto": r.versione_contratto, "documento_id": str(doc.id),
                        "sha256_documento": doc.sha256,
                        "pagine": [p.model_dump(mode="json") for p in r.pagine]}, ensure_ascii=False).encode()
    rif_doc = RiferimentoArchivio(doc.archivio.value, doc.id_archivio, doc.sha256, doc.dimensione or 0)
    try:
        rif_testo = archivio.salva_accanto(rif_doc, "testo.json", testo)
        if archivio.impronta(rif_testo.id_archivio) != rif_testo.sha256:
            raise ErroreArchivio("impronta del testo non coincide")
    except ErroreArchivio:
        return _fallisci(db, lavoro, "salvataggio_testo", True)
    doc.id_archivio_testo, doc.sha256_testo, doc.tipo_documento = rif_testo.id_archivio, rif_testo.sha256, r.tipo_documento.valore
    ris = RisultatoMotore(
        lavoro_id=lavoro.id, documento_id=doc.id, pratica_id=doc.pratica_id,
        versione_motore=r.versione_motore, versione_contratto=r.versione_contratto,
        tipo_documento=r.tipo_documento.valore, tipo_documento_motivo=r.tipo_documento.motivo,
        protocollo_letto=r.protocollo.numero if r.protocollo else None,
        data_protocollo_letta=r.protocollo.data if r.protocollo else None,
        lettura_incerta=r.lettura_incerta, pagine_incerte=r.pagine_incerte,
        acquisizione={str(p.numero): p.acquisizione for p in r.pagine},
        scheda=r.scheda.model_dump(mode="json"), proposta=r.proposta.model_dump(mode="json"),
        temi_proposti=[t.model_dump(mode="json") for t in r.temi])
    db.add(ris)
    db.flush()
    if db.get(Pratica, doc.pratica_id).documento_principale_id == doc.id:
        nuovi = proponi_temi(db, doc.pratica_id, ris)
        if nuovi:
            registra(db, utente_id=None, azione="temi.proponi", oggetto_tipo="pratica", oggetto_id=doc.pratica_id,
                     pratica_id=doc.pratica_id, dettagli={"temi": nuovi})
    lavoro.stato, lavoro.finito_il, lavoro.codice_errore = StatoLavoro.completato, _ora(), None
    registra(db, utente_id=None, azione="motore.completato", oggetto_tipo="lavoro_motore", oggetto_id=lavoro.id,
             pratica_id=lavoro.pratica_id,
             dettagli={"documento_id": str(doc.id), "versione_motore": r.versione_motore,
                       "lettura_incerta": r.lettura_incerta, "pagine": len(r.pagine)})
    db.flush()
    _concludi_pratica_se_pronta(db, lavoro.pratica_id)
    db.commit()
    return Esito("completato")


def _concludi_pratica_se_pronta(db: Session, pratica_id: uuid.UUID) -> None:
    """Chiuse tutte le analisi: IN_ANALISI → DA_SMISTARE (transizione del sistema).
    Si precompilano solo i dati ancora vuoti; ufficio, valutazione e temi restano alle persone."""
    aperti = db.execute(select(LavoroMotore.id).where(
        LavoroMotore.pratica_id == pratica_id,
        LavoroMotore.stato.in_([StatoLavoro.in_coda, StatoLavoro.in_corso])).limit(1)).first()
    pratica = db.execute(select(Pratica).where(Pratica.id == pratica_id).with_for_update(of=Pratica)).scalar_one()
    if aperti or pratica.stato != Stato.IN_ANALISI:
        return
    dettagli: dict = {}
    if pratica.documento_principale_id:
        ris = db.execute(select(RisultatoMotore).where(RisultatoMotore.documento_id == pratica.documento_principale_id)
                         .order_by(RisultatoMotore.ricevuto_il.desc()).limit(1)).scalar_one_or_none()
        if ris:
            if ris.tipo_documento != pratica.tipo:
                dettagli["tipo"] = {"prima": pratica.tipo, "dopo": ris.tipo_documento}
                pratica.tipo = ris.tipo_documento
            if not pratica.protocollo and ris.protocollo_letto:
                pratica.protocollo, pratica.data_protocollo = ris.protocollo_letto, ris.data_protocollo_letta
                dettagli["protocollo"] = ris.protocollo_letto
            comune = (ris.scheda.get("comune") or {}).get("valore")
            if not pratica.comune and comune:
                pratica.comune = comune
                dettagli["comune"] = comune
    db.add(CambioStato(pratica_id=pratica.id, da_stato=pratica.stato, a_stato=Stato.DA_SMISTARE, utente_id=None))
    pratica.stato = Stato.DA_SMISTARE
    pratica.versione += 1
    pratica.aggiornata_il = _ora()
    registra(db, utente_id=None, azione="pratica.analisi_conclusa", oggetto_tipo="pratica", oggetto_id=pratica.id,
             pratica_id=pratica.id, dettagli=dettagli or None)


# --- elaborazione di un lavoro ---------------------------------------------------------------

def elabora(db: Session, lavoro: LavoroMotore, *, client: ClientMotore, archivio: ArchivioDocumenti,
            dormi: Callable[[float], None] = time.sleep) -> Esito:
    cfg = get_settings()
    doc = db.get(Documento, lavoro.documento_id)
    id_invio = str(uuid.uuid5(lavoro.id, str(lavoro.tentativi)))  # nuovo id a ogni tentativo
    tmp = tempfile.mkdtemp(prefix=PREFISSO_TEMP, dir=cartella_temporanea())
    consegnato = False
    try:
        locale = Path(tmp) / "documento"
        try:
            with archivio.apri(doc.id_archivio) as src, open(locale, "wb") as dst:
                shutil.copyfileobj(src, dst)
            if archivio.impronta(doc.id_archivio) != doc.sha256:
                raise ErroreArchivio("impronta diversa da quella registrata")
        except ErroreArchivio:
            return _fallisci(db, lavoro, "archivio_non_disponibile", False)

        pratica = db.get(Pratica, doc.pratica_id)
        contesto = {"protocollo_noto": pratica.protocollo, "canale": pratica.canale.value} if pratica.protocollo else None
        try:
            with open(locale, "rb") as f:
                client.invia(id_lavoro=id_invio, documento=f, nome_file=doc.nome_file, tipo_mime=doc.tipo_mime,
                             documento_id=str(doc.id), sha256=doc.sha256, contesto=contesto)
            consegnato = True
        except MotoreOccupato as e:
            lavoro.stato, lavoro.tentativi = StatoLavoro.in_coda, max(0, lavoro.tentativi - 1)
            db.commit()
            return Esito("occupato", attesa=e.retry_after)
        except MotoreRifiuto as e:
            return _fallisci(db, lavoro, e.errore.codice, e.errore.ritentabile)
        except MotoreIrraggiungibile as e:
            return _fallisci(db, lavoro, "errore_interno", True, {"causa": str(e)})

        scadenza = time.monotonic() + cfg.motore_timeout_secondi
        while True:
            try:
                st = client.stato(id_invio)
            except RisultatoNonValido as e:
                return _fallisci(db, lavoro, "risultato_non_valido", False, {"campi": e.percorsi})
            except MotoreIrraggiungibile as e:
                return _fallisci(db, lavoro, "errore_interno", True, {"causa": str(e)})
            if st.stato == "completato":
                esito = _salva_risultato(db, lavoro, doc, st.risultato, archivio)
                if esito.tipo == "completato":
                    try:
                        client.conferma(id_invio)  # solo dopo il salvataggio verificato
                    except MotoreIrraggiungibile:
                        log.warning("conferma al motore non riuscita (lavoro %s)", lavoro.id)
                    consegnato = False
                return esito
            if st.stato == "errore":
                return _fallisci(db, lavoro, st.errore.codice, st.errore.ritentabile)
            if time.monotonic() > scadenza:
                return _fallisci(db, lavoro, "tempo_scaduto", True, {"origine": "applicazione"})
            dormi(cfg.motore_intervallo_secondi)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # sempre
        if consegnato:
            try:
                client.conferma(id_invio)  # il motore non deve tenere nulla di un lavoro concluso male
            except MotoreIrraggiungibile:
                pass


def esegui_coda(*, client: ClientMotore | None = None, archivio: ArchivioDocumenti | None = None,
                dormi: Callable[[float], None] = time.sleep, max_attese_occupato: int = 50) -> dict[str, int]:
    """Svuota la coda, un lavoro alla volta. Restituisce i conteggi per esito."""
    client, archivio = client or get_client(), archivio or get_archivio()
    conteggi: dict[str, int] = {}
    attese = 0
    with get_sessionmaker()() as db:
        riprendi_interrotti(db)
    while True:
        with get_sessionmaker()() as db:
            lavoro = prendi_prossimo(db)
            if lavoro is None:
                return conteggi
            esito = elabora(db, lavoro, client=client, archivio=archivio, dormi=dormi)
        if esito.tipo == "occupato":
            attese += 1
            if attese > max_attese_occupato:
                return conteggi
            dormi(esito.attesa)
            continue
        conteggi[esito.tipo] = conteggi.get(esito.tipo, 0) + 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Worker della coda del motore")
    ap.add_argument("--una-volta", action="store_true", help="svuota la coda ed esce")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    rimossi = pulisci_temporanei()
    if rimossi:
        log.info("temporanei rimasti da un avvio precedente: %d, cancellati", rimossi)
    while True:
        conteggi = esegui_coda()
        if conteggi:
            log.info("lavori elaborati: %s", conteggi)
        if args.una_volta:
            print(conteggi or "coda vuota")
            return
        time.sleep(get_settings().motore_intervallo_secondi)


if __name__ == "__main__":
    main()
