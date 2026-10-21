"""GET /api/v1/salute: database, archivio, coda dei lavori, motore.

Codice HTTP: 503 se database o archivio non funzionano (l'applicazione non può lavorare);
200 negli altri casi, anche con il motore irraggiungibile o con un contratto diverso
(«degradato»): il lavoro delle persone non si blocca senza il motore, e i lavori restano in coda.
La risposta non contiene URL, percorsi né messaggi d'errore interni.
"""
import httpx
from sqlalchemy import func, select, text

from motore.client import MotoreHttp, MotoreIrraggiungibile
from motore.contratto import VERSIONE_CONTRATTO

from .archivio import get_archivio
from .config import get_settings
from .db import get_engine
from .enums import StatoLavoro
from .models import LavoroMotore

TIMEOUT_MOTORE_SECONDI = 2.0


def _database() -> str:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "errore"


def _archivio() -> str:
    try:
        get_archivio().verifica()
        return "ok"
    except Exception:
        return "errore"


def _coda() -> dict:
    try:
        with get_engine().connect() as conn:
            conteggi = dict(conn.execute(
                select(LavoroMotore.stato, func.count()).where(
                    LavoroMotore.stato.in_([StatoLavoro.in_coda, StatoLavoro.in_corso]))
                .group_by(LavoroMotore.stato)).all())
        return {"stato": "ok", "in_coda": conteggi.get(StatoLavoro.in_coda, 0),
                "in_corso": conteggi.get(StatoLavoro.in_corso, 0)}
    except Exception:
        return {"stato": "errore", "in_coda": None, "in_corso": None}


def _stessa_versione_principale(a: str, b: str) -> bool:
    return a.split(".")[0] == b.split(".")[0]


def _motore() -> dict:
    url = get_settings().motore_url
    if not url:
        # finto motore nello stesso processo del worker: niente da raggiungere
        return {"stato": "in_processo", "versione_motore": None, "versione_contratto": VERSIONE_CONTRATTO,
                "contratto_compatibile": True, "occupato": None}
    try:
        with httpx.Client(base_url=url, timeout=TIMEOUT_MOTORE_SECONDI) as c:
            s = MotoreHttp(http_client=c).salute()
    except MotoreIrraggiungibile:
        return {"stato": "irraggiungibile", "versione_motore": None, "versione_contratto": None,
                "contratto_compatibile": None, "occupato": None}
    compatibile = _stessa_versione_principale(s.versione_contratto, VERSIONE_CONTRATTO)
    return {"stato": "ok" if compatibile else "contratto_diverso", "stato_dichiarato": s.stato,
            "versione_motore": s.versione_motore,
            "versione_contratto": s.versione_contratto, "contratto_compatibile": compatibile,
            "occupato": s.occupato}


def salute() -> tuple[int, dict]:
    database, archivio = _database(), _archivio()
    coda = _coda() if database == "ok" else {"stato": "errore", "in_coda": None, "in_corso": None}
    motore = _motore()
    if database != "ok" or archivio != "ok":
        stato, codice = "errore", 503
    elif motore["stato"] in ("ok", "in_processo") and coda["stato"] == "ok":
        stato, codice = "ok", 200
    else:
        stato, codice = "degradato", 200
    return codice, {"stato": stato, "database": database, "archivio": archivio, "coda": coda,
                    "motore": motore, "versione_contratto_applicazione": VERSIONE_CONTRATTO}
