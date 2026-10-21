"""Registro delle azioni: chi, cosa, quando, su cosa.

Va chiamato nella stessa transazione della scrittura che documenta.
`dettagli` non deve mai contenere testo di documenti né password.
"""
import uuid
from contextvars import ContextVar

from sqlalchemy.orm import Session

from .models import RegistroAzioni

id_richiesta_corrente: ContextVar[str | None] = ContextVar("id_richiesta", default=None)


def registra(
    db: Session,
    *,
    utente_id: uuid.UUID | None,
    azione: str,
    oggetto_tipo: str,
    oggetto_id: uuid.UUID | str | None = None,
    pratica_id: uuid.UUID | None = None,
    dettagli: dict | None = None,
) -> None:
    db.add(RegistroAzioni(
        utente_id=utente_id,
        azione=azione,
        oggetto_tipo=oggetto_tipo,
        oggetto_id=str(oggetto_id) if oggetto_id is not None else None,
        pratica_id=pratica_id,
        dettagli=dettagli,
        id_richiesta=id_richiesta_corrente.get(),
    ))
