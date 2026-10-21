import datetime as dt
import uuid

from sqlalchemy.orm import Session

from .enums import StatoLavoro
from .models import Documento, LavoroMotore
from .registro import registra


def accoda(db: Session, documento: Documento, richiesto_da: uuid.UUID | None) -> LavoroMotore:
    lavoro = LavoroMotore(documento_id=documento.id, pratica_id=documento.pratica_id,
                          stato=StatoLavoro.in_coda, tentativi=0, richiesto_da=richiesto_da,
                          richiesto_il=dt.datetime.now(dt.timezone.utc))  # ordine di arrivo anche nella stessa transazione
    db.add(lavoro)
    db.flush()
    registra(db, utente_id=richiesto_da, azione="motore.accoda", oggetto_tipo="lavoro_motore",
             oggetto_id=lavoro.id, pratica_id=documento.pratica_id,
             dettagli={"documento_id": str(documento.id), "automatico": richiesto_da is None})
    return lavoro
