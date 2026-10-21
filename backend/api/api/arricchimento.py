"""Righe di elenco arricchite (temi, esito, avviso, disaccordo, collegate) con poche query per pagina."""
import uuid
from collections import defaultdict

from sqlalchemy import func, or_, select, union_all
from sqlalchemy.orm import Session

from .enums import StatoTema
from .models import (
    Collegamento, Pratica, PraticaTema, RisultatoMotore, Tema, Valutazione, vista_analisi_principale,
)
from .schemas import EsitoRiga, PraticaRiga, PropostaRiga
from .valutazione import disaccordo_per


def arricchisci(db: Session, pratiche: list[Pratica]) -> list[PraticaRiga]:
    ids = [p.id for p in pratiche]
    if not ids:
        return []
    temi: dict[uuid.UUID, list[str]] = defaultdict(list)
    for pid, nome in db.execute(select(PraticaTema.pratica_id, Tema.nome).join(Tema, Tema.id == PraticaTema.tema_id)
                                .where(PraticaTema.pratica_id.in_(ids), PraticaTema.stato == StatoTema.confermato)
                                .order_by(Tema.ordine, Tema.codice)):
        temi[pid].append(nome)
    valutazioni = {v.pratica_id: v for v in db.execute(select(Valutazione).where(Valutazione.pratica_id.in_(ids))).scalars()}
    ap = vista_analisi_principale
    proposte, incerte = {}, set()
    for pid, incerta, proposta in db.execute(
            select(ap.c.pratica_id, ap.c.lettura_incerta, RisultatoMotore.proposta)
            .join(RisultatoMotore, RisultatoMotore.id == ap.c.risultato_id).where(ap.c.pratica_id.in_(ids))):
        proposte[pid] = PropostaRiga(esito=proposta.get("esito"), urgenza=proposta.get("urgenza"))
        if incerta:
            incerte.add(pid)
    disaccordi = disaccordo_per(db, ids)

    # collegate: manuali attivi (da entrambi i lati) + automatiche (stesso protocollo, altre pratiche)
    lati = union_all(
        select(Collegamento.pratica_da_id.label("p")).where(Collegamento.rimosso_il.is_(None),
                                                            Collegamento.pratica_da_id.in_(ids)),
        select(Collegamento.pratica_a_id.label("p")).where(Collegamento.rimosso_il.is_(None),
                                                           Collegamento.pratica_a_id.in_(ids))).subquery()
    n_manuali = dict(db.execute(select(lati.c.p, func.count()).group_by(lati.c.p)).all())
    protocolli = {p.protocollo for p in pratiche if p.protocollo}
    per_protocollo = dict(db.execute(select(Pratica.protocollo, func.count()).where(Pratica.protocollo.in_(protocolli))
                                     .group_by(Pratica.protocollo)).all()) if protocolli else {}

    out = []
    for p in pratiche:
        v = valutazioni.get(p.id)
        riga = PraticaRiga.model_validate(p)
        riga.temi = temi.get(p.id, [])
        riga.valutazione = EsitoRiga(esito=v.esito, urgenza=v.urgenza, origine=v.origine, compilata=v.compilata) if v else None
        riga.proposta = proposte.get(p.id)
        riga.lettura_incerta = p.id in incerte
        riga.disaccordo = disaccordi.get(p.id, [])
        riga.n_collegate = n_manuali.get(p.id, 0) + (per_protocollo.get(p.protocollo, 1) - 1 if p.protocollo else 0)
        out.append(riga)
    return out
